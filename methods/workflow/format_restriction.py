import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


def load_jsonl(path):
    datas = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            datas.append(data)
    return datas


samples = load_jsonl("/Users/ryan/Projects/Spider2/spider2-lite/spider2-lite.jsonl")
model_name = "qwen2.5-72b-instruct"
llm = ChatOpenAI(
    temperature=0.01,
    openai_api_base="http://127.0.0.1:8081/v1",
    openai_api_key="NONE",
    model=model_name,
    max_tokens=8192,
)
# TODO prompt
# 根据现在的输入问题，生成它需要的格式
# 可以举几个例子，如最大值、百分比这些
format_restriction = """You'll be given a text-to-SQL question where the outcome of the corresponding SELECT query is guaranteed to return values. 
Your sole task is to generate a set of formatting requirements for the query result. 
The requirements should strictly focus on formatting and not involve guiding the text-to-SQL generation process.

Here are some key principles to follow:
Columns must be explicitly defined with clear headers, and each record should be on a separate row for easy readability.
The format should handle special data types in a concise and unambiguous way.
For any potential ambiguities in the result, additional columns or clear notations can be added.

Based on these, generate a well-structured set of formatting requirements for the result of the upcoming SELECT statement. 
Avoid including any details about how to construct the SQL query itself.

question:{question}
formatting requirements:"""

# TODO self-refine
# 在迭代中需要检查和强化这个格式
prompt_result_format = """
################### TASK ###################
Please Solve this task:
{question}

Result format:
{format}

The final result MUST be a CSV file, not an .sql file, a calculation, an idea, a sentence or merely an intermediate step. 
Save the answer as a CSV and the file name should be `result.csv`, it is usually from the SQL execution result.
If there is a 'result.csv' in the initial folder, the format of your answer must match it.
"""


PROMPT = ChatPromptTemplate.from_messages([("user", format_restriction)])
chain = PROMPT | llm | StrOutputParser()
# TODO 测试一下 format 生成的质量
for sample in samples:
    resp = chain.invoke(
        input={
            "question": sample["question"],
        },
    )
    print(resp)
