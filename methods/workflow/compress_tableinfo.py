import os
import re
from collections import defaultdict
from copy import deepcopy

import diff_match_patch
import pandas as pd


def compare_ddl(ddl1, ddl2):
    # 创建 diff_match_patch 实例
    dmp = diff_match_patch.diff_match_patch()
    # 生成差异信息
    diffs = dmp.diff_main(ddl1, ddl2)
    # 清理差异信息以提高可读性
    dmp.diff_cleanupSemantic(diffs)

    resp = ""
    for diff in diffs:
        op, data = diff
        if op == dmp.DIFF_INSERT:
            print(f"新增: {data}")
            resp += data
        elif op == dmp.DIFF_DELETE:
            print(f"删除: {data}")
            resp += data
    diff_ratio = len(resp) / min(len(ddl1), len(ddl2))
    print(f"差异率: {diff_ratio}")
    return diff_ratio


def find_common_prefix_suffix(strings):
    prefix_dict = defaultdict(list)
    suffix_dict = defaultdict(list)

    for s in strings:
        parts = []
        # Split by both '_' and '-'
        for char in ["_", "-"]:
            if char in s:
                parts = s.split(char)
                break

        if len(parts) > 1:
            # Attempt to add to prefix_dict
            prefix = "_".join(parts[:-1])
            prefix_dict[prefix].append(s)

            # Attempt to add to suffix_dict
            suffix = parts[-1]
            suffix_dict[suffix].append(s)

    # Filter out entries with less than 2 items
    prefix_dict = {k: v for k, v in prefix_dict.items() if len(v) > 1}
    suffix_dict = {k: v for k, v in suffix_dict.items() if len(v) > 1}

    # Ensure items do not appear in both dictionaries
    for k, v in list(prefix_dict.items()):
        for item in v:
            for sk in list(suffix_dict.keys()):
                if item in suffix_dict[sk]:
                    suffix_dict[sk].remove(item)
                    if not suffix_dict[sk]:
                        del suffix_dict[sk]

    # Create merged list of unique prefixes and suffixes used as keys in the dicts
    merged_list = list(set(list(prefix_dict.keys()) + list(suffix_dict.keys())))

    return merged_list, prefix_dict, suffix_dict


def add_ddl_to_merge_dict(merge_dict, ddl_dict):
    if len(merge_dict) == 0:
        return merge_dict

    new_merge_dict = {}
    for compressed_table_name, table_names in merge_dict.items():
        print(f"check ddl: {compressed_table_name}")
        ddl_patterns = dict()
        for table_name in table_names:
            ddl = ddl_dict[table_name]["ddl"]
            # 删除表名
            ddl_c = re.sub(
                r"CREATE TABLE `[^`]+`", "CREATE TABLE `{table}`", ddl
            )  # ddl clean
            if ddl_c in ddl_patterns.keys():
                ddl_patterns[ddl_c].append(table_name)
            else:
                ddl_patterns[ddl_c] = []
                ddl_patterns[ddl_c].append(table_name)

        ddl_patterns_keys = list(ddl_patterns.keys())
        ddl_patterns_merged = deepcopy(ddl_patterns)
        diff_threshold = 0.05
        has_merged = []

        for ddl1 in ddl_patterns_keys:
            for ddl2 in ddl_patterns_keys:
                if ddl1 == ddl2 or ddl1 in has_merged or ddl2 in has_merged:
                    pass
                else:
                    diff_ratio = compare_ddl(ddl1, ddl2)
                    if diff_ratio < diff_threshold:
                        if len(ddl1) > len(ddl2):
                            has_merged.append(ddl2)
                            ddl_patterns_merged[ddl1] = (
                                ddl_patterns_merged[ddl1] + ddl_patterns_merged[ddl2]
                            )
                            del ddl_patterns_merged[ddl2]

                        else:
                            has_merged.append(ddl1)
                            ddl_patterns_merged[ddl2] = (
                                ddl_patterns_merged[ddl1] + ddl_patterns_merged[ddl2]
                            )
                            del ddl_patterns_merged[ddl1]

        # 确保 merge 之后没有丢失或增加
        assert sum(map(len, ddl_patterns.values())) == sum(
            map(len, ddl_patterns_merged.values())
        ), "not fetch"

        # add to new
        new_merge_dict[compressed_table_name] = []
        if len(ddl_patterns_merged) == 1:
            new_merge_dict[compressed_table_name].append(
                {
                    "merged_name": compressed_table_name,
                    "ddl": list(ddl_patterns_merged.keys())[0].format(
                        table=compressed_table_name
                    ),
                    "tables": list(ddl_patterns_merged.values())[0],
                }
            )
        else:
            for i in range(len(ddl_patterns_merged.keys())):
                # 如果做完 diff_ratio 处理后，一个 ddl_pattern 只有一个table 那就没有必要用 prefix 或 suffix 了
                _tables = list(ddl_patterns_merged.values())[i]
                if len(_tables) > 1:
                    new_merge_dict[compressed_table_name].append(
                        {
                            "merged_name": f"{compressed_table_name}_{i}",
                            "ddl": list(ddl_patterns_merged.keys())[0].format(
                                table=f"{compressed_table_name}_{i}"
                            ),
                            "tables": _tables,
                        }
                    )
                else:
                    _table_name = _tables[0]
                    new_merge_dict[compressed_table_name].append(
                        {
                            "merged_name": _table_name,
                            "ddl": list(ddl_patterns_merged.keys())[0].format(
                                table=_table_name
                            ),
                            "tables": _tables,
                        }
                    )

    return new_merge_dict


path_to_spider2lite = "methods/workflow/examples"
task = "bq032"
stuffs = os.listdir(os.path.join(path_to_spider2lite, task))

for stuff in stuffs:
    path_to_stuff = os.path.join(path_to_spider2lite, task, stuff)
    if os.path.isdir(path_to_stuff):
        path_to_workspace = path_to_stuff
    elif path_to_stuff.endswith(".md"):
        path_to_knowledge = path_to_stuff
    elif path_to_stuff.endswith("credential.json"):
        path_to_credential = path_to_stuff
    else:
        raise Exception(f"unknown type: {path_to_stuff}")
for db in os.listdir(path_to_workspace):
    path_to_db = os.path.join(path_to_workspace, db)
    if os.path.isdir(path_to_db):
        print(f"now in db: {path_to_db}")
        assert "DDL.csv" in os.listdir(path_to_db), "No 'DDL.csv' found."
        tables = [
            table.split(".json")[0]
            for table in os.listdir(path_to_db)
            if table.endswith(".json")
        ]
        compressed_tables, prefix_dict, suffix_dict = find_common_prefix_suffix(tables)

        # TODO 二次验证：prefix\suffix 里的表格的确是建表语句重复
        # 在 DDL.csv 中验证
        ddls = pd.read_csv(os.path.join(path_to_db, "DDL.csv"))
        assert "table_name" in ddls.columns
        assert "ddl" in ddls.columns
        ddl_dict = ddls.set_index("table_name").to_dict(orient="index")

        # add
        prefix_dict = add_ddl_to_merge_dict(prefix_dict, ddl_dict)
        suffix_dict = add_ddl_to_merge_dict(suffix_dict, ddl_dict)

        # TODO 给出压缩后的表格信息
        compressed_tableinfo = ""
        for table_name in compressed_tables:

            if table_name in prefix_dict.keys():
                for d in prefix_dict[table_name]:
                    compressed_tableinfo += d["ddl"] + "\n"

            elif table_name in suffix_dict.keys():
                for d in suffix_dict[table_name]:
                    compressed_tableinfo += d["ddl"] + "\n"

            else:
                # 无法压缩的信息，从ddl_dict 中提取ddl
                compressed_tableinfo += ddl_dict[table_name]["ddl"] + "\n"
        print(compressed_tableinfo)
    else:
        raise Exception(f"unknown db: {path_to_db}")
