import glob
import json
import os
import re

import pandas as pd
from sql_metadata import Parser


def load_json(data_path):
    """
    # 加载 json 文件
    """
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def extract_last_sql(trajectory: list):
    def is_sql(action: str):
        if (
            action.startswith("SNOWFLAKE_EXEC_SQL")
            or action.startswith("BIGQUERY_EXEC_SQL")
            or action.startswith("LOCAL_DB_SQL")
        ):
            return action

        else:
            return False

    for traj in trajectory[::-1]:
        action = traj["action"]
        if is_sql(action):
            pattern = r'(?:sql_query|command)=(?:"(.*?)"|"""(.*?)""")'
            match = re.search(pattern, action, re.DOTALL)
            if match:
                return match.group(1)
            else:
                raise Exception(f"sql extraction failed: {action}")
    return None


def calc_table_reacll_acc(sql_gen, task):
    def load_sqlfile(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            sql = file.read()
        return sql

    def extract_table(sql_query):
        if "SELECT" in sql_query.upper():
            try:
                return Parser(sql_query).tables
            except Exception:
                return None
        else:
            return []

    gold_path = os.path.join(gold_sql_folder, f"{task}.sql")
    if not os.path.exists(gold_path):
        return "gold_not_exist", 0

    if sql_gen is None:
        return "llm_sql_not_exist", 0

    else:
        sql_gold = load_sqlfile(gold_path)
        tables_gold = extract_table(sql_gold)
        tables_gen = extract_table(sql_gen)

        # 计算命中 gold 的表格数量
        if tables_gold is None:
            return "gold_parse_error", 0

        if tables_gen is None:
            return "llm_sql_parse_error", 0

        return "parsed", len(set(tables_gen) & set(tables_gold)) / len(set(tables_gold))


def extract_action(action: str):
    if action.startswith("Bash"):
        return "os"
    elif (
        action.startswith("SNOWFLAKE_EXEC_SQL")
        or action.startswith("BIGQUERY_EXEC_SQL")
        or action.startswith("LOCAL_DB_SQL")
    ):
        return "sql"
    elif action.startswith("Terminate"):
        return "end"
    else:
        # print(action)
        return "unkown"


gold_sql_folder = "/Users/ryan/Projects/Spider2/spider2-lite/evaluation_suite/gold/sql"
folder = "/Users/ryan/Projects/Spider2/methods/spider-agent-lite/output"
# task = "gpt-4o-20250212"
task = "tablegpt2-7b-20250212"

# 定义要搜索的目录和模式
pattern = os.path.join(folder, task, "*", "spider", "result.json")

# 使用glob.glob来查找所有匹配的文件
matched_files = glob.glob(pattern)


# 打印所有匹配到的文件路径
ana_exec = pd.DataFrame()
ana_recall = pd.DataFrame()
for file_path in matched_files:
    task_id = re.search(r"([^/]+)/spider/", file_path).group(1)
    # 分析最后一个动作
    resp = load_json(file_path)
    tag_success = resp["finished"]
    last_action = extract_action(resp["trajectory"][-1]["action"])
    # 分析最后一句 SQL
    # TODO 增加对选表准确性的分析，对比gold
    last_sql = extract_last_sql(resp["trajectory"])
    tag_recall, acc = calc_table_reacll_acc(last_sql, task_id)
    ana_recall = ana_recall._append(
        {"task": task_id, "tag": tag_recall, "acc": acc}, ignore_index=True
    )

    ana_exec = ana_exec._append(
        {"executable": tag_success, "action": last_action}, ignore_index=True
    )
# ana_exec["cnt"] = 1
# print(task)
# new = pd.DataFrame(ana_exec.groupby(["executable", "action"])["cnt"].sum())
# new["ratio"] = ["{:.2f}%".format(100 * cnt / new["cnt"].sum()) for cnt in new["cnt"]]
# new.reset_index(drop=False, inplace=True)
# new = new._append({"cnt": new["cnt"].sum(), "ratio": "100%"}, ignore_index=True)
# new.to_excel("./{}.xlsx".format(task))
# print(new)


# recall
ana_recall["cnt"] = 1
res = (
    ana_recall[["tag", "acc", "cnt"]].groupby("tag").agg({"acc": "mean", "cnt": "sum"})
)
res.to_excel("./{}_recall.xlsx".format(task))
print(res)
