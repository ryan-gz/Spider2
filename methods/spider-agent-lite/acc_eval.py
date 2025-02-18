import glob
import json
import os

import pandas as pd


def load_json(data_path):
    """
    # 加载 json 文件
    """
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


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


folder = "/Users/ryan/Projects/Spider2/methods/spider-agent-lite/output"
# task = "gpt-4o-20250212"
task = "tablegpt2-7b-20250212"

# 定义要搜索的目录和模式
pattern = os.path.join(folder, task, "*", "spider", "result.json")

# 使用glob.glob来查找所有匹配的文件
matched_files = glob.glob(pattern)

# 打印所有匹配到的文件路径
ana = pd.DataFrame()
for file_path in matched_files:
    # print(file_path)
    resp = load_json(file_path)
    tag_success = resp["finished"]
    last_action = extract_action(resp["trajectory"][-1]["action"])
    ana = ana._append(
        {"executable": tag_success, "action": last_action}, ignore_index=True
    )
ana["cnt"] = 1
print(task)
new = pd.DataFrame(ana.groupby(["executable", "action"])["cnt"].sum())
new["ratio"] = ["{:.2f}%".format(100 * cnt / new["cnt"].sum()) for cnt in new["cnt"]]
new.reset_index(drop=False, inplace=True)
new = new._append({"cnt": new["cnt"].sum(), "ratio": "100%"}, ignore_index=True)
new.to_excel("./{}.xlsx".format(task))
print(new)
