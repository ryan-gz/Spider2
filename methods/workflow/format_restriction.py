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
# Enhanced prompt for generating formatting requirements
format_restriction = """You'll be given a text-to-SQL question where the outcome of the corresponding SELECT query is guaranteed to return values. 
Your sole task is to generate a set of formatting requirements for the query result. 
The requirements should strictly focus on formatting and not involve guiding the text-to-SQL generation process.

Here are some key principles to follow:
1. The format should account for specific cases, such as superlatives, percentages, or coordinates, ensuring the output is concise, clear, and unambiguous.
2. For ambiguous terms, potential values or additional columns can be added to maintain clarity and precision.
3. For any potential ambiguities in the result, additional columns or clear notations can be added.
4. Include units of measurement where applicable (e.g., currency, weight, distance).
5. If the result is expected to be unique, make answer in one row.
6. Source name should be displayed in its original form as it appears in the data. 
7. Don't lable any column headers, column names, table names, or any other SQL query components.

The final result MUST be a CSV file, not an .sql file, a calculation, an idea, a sentence or merely an intermediate step. 
Save the answer as a CSV and the file name should be `result.csv`, it is usually from the SQL execution result.
If there is a 'result.csv' in the initial folder, the format of your answer must match it.

Based on these, generate a well-structured set of formatting requirements for the result of the upcoming SELECT statement. 
Avoid including any details about how to construct the SQL query itself.

question:{question}
formatting requirements:"""

# Define the self-refinement prompt
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

# Test the format generation quality
for sample in samples:
    resp = chain.invoke(
        input={
            "question": sample["question"],
        },
    )
    print(sample["question"])
    print(resp)
