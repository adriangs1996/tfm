import re
import sys
import os
from typing import Dict, Optional
from ollama import Client, Message, Options
from categorize import classify_file
from vecstore import Category

POSSIBLE_CATEGORIES = [cat.value for cat in Category] + ["bcrypt"]

options = Options(temperature=0.0)


def identify_algorithm(code: str, algorithm_name: str, explanation=None):
    print(algorithm_name)
    return (algorithm_name, code, explanation)


AVAILABLE_FUNCTIONS = {"identify_algorithm": identify_algorithm}

def get_true_category_v2_codellama(file_path, categories):
    question = open(file_path).read()
    prompt = f"""
    You are a machine capable of recognizing algorithms or fragments of use of algorithms.
    Given the following code, identify if it is an implementation of a cryptographic
    algorithm,  the use of a cryptographic algorithm, or it is just a general
    code. Take into account that a use of cryptographic code can be considered
    anything that tries to hash a password, digest a message, sign a token, or
    pretty much anything that would be considered the use of a cryptographic primitive.

    If the algorithm is an example of use of any cryptographic primitive, the possible
    categories are:
    - USES_AES: in case the algorithm is using the AES algorithm.
    - PASSWORD_PBKDF2_SHA256: in case it is using a key derivation algorithm.
    - PASSWORD_BCRYPT: in case it is using the bcrypt algorithm.

    If the algorithm is an implementation, then the possible categories are:
    - RSA
    - DiffieHellman
    - DSA
    - ElipticCurves
    - ED448
    - ED25519
    - AES
    - CAMELLIA
    - CHACHA20
    - DES
    - HMAC
    - MD5
    - SHA

    If the code is not implementing nor using any cryptographic primitive, then the
    output should be NO_CRYPTO.

    The code is as follow:
    {question}

    If usefull, a previous model has classified this code as one of these categories:
    {", ".join(categories)}

    OUTPUT ONLY THE CATEGORY OF THE ALGORITHM AND NOTHING ELSE.
    """
    client = Client(host="http://localhost:11434")
    llm_response: Dict = client.generate(
        model="llama3.1",
        prompt=prompt,
        options=options,
    )  # type: ignore
    answer = llm_response.get("response", {})
    regexes = [
        re.compile(f"""({'|'.join(POSSIBLE_CATEGORIES)})"""),
        re.compile(r"SHA\-256|SHA256|SHA\-1|SHA1|SHA\-512|SHA512|SHA\-3|SHA3"),
    ]
    matches = [regex.search(answer.strip()) for regex in regexes]
    if any(m is not None for m in matches):
        match = next(m for m in matches if m is not None)
        return "LLM " + match.group(1).strip()
    else:
        return answer.strip()


def get_true_category(file_path, categories):
    question = open(file_path).read()
    prompt = f"""
    You are a machine capable of recognizing algorithms or fragments of use of algorithms.
    Given the following code, identify if it is an implementation of a cryptographic
    algorithm,  the use of a cryptographic algorithm, or it is just a general
    code. Take into account that a use of cryptographic code can be considered
    anything that tries to hash a password, digest a message, sign a token, or
    pretty much anything that would be considered the use of a cryptographic primitive.

    If the algorithm is an example of use of any cryptographic primitive, the possible
    categories are:
    - USES_AES: in case the algorithm is using the AES algorithm.
    - PASSWORD_PBKDF2_SHA256: in case it is using a key derivation algorithm.
    - PASSWORD_BCRYPT: in case it is using the bcrypt algorithm.

    If the algorithm is an implementation, then the possible categories are:
    - RSA
    - DiffieHellman
    - DSA
    - ElipticCurves
    - ED448
    - ED25519
    - AES
    - CAMELLIA
    - CHACHA20
    - DES
    - HMAC
    - MD5
    - SHA

    If the code is not implementing nor using any cryptographic primitive, then the
    output should be NO_CRYPTO.

    The code is as follow:
    {question}
    """
    client = Client(host="http://localhost:11434")
    llm_response: Dict = client.chat(
        model="llama3.1",
        messages=[Message(content=prompt, role="user")],
        options=options,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "identify_algorithm",
                    "description": "This function identifies a given fragment of code by name. It is used to detect cryptographic code.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "The code that was identified as with the algorithm_name parameter",
                            },
                            "algorithm_name": {
                                "type": "string",
                                "description": "The identified algorithm name or NO_CRYPTO if it is not a cryptographic code",
                            },
                            "explanation": {
                                "type": "string",
                                "description": "An explanation of why the algorithm is identified by that name",
                            },
                        },
                        "required": ["algorithm_name", "code", "explanation"],
                    },
                },
            }
        ],
    )  # type: ignore
    print(llm_response)
    if tool_calls := llm_response["message"].get("tool_calls", None):
        for function_to_call in tool_calls:  # type: ignore
            func = AVAILABLE_FUNCTIONS[function_to_call["function"]["name"]]  # type: ignore
            args = function_to_call["function"]["arguments"]
            if "description" in args:
                desc = args.pop("description")
                args['explanation'] = desc

            return func(**args)[0]

    answer = llm_response.get("message", {}).get("content", {})
    regexes = [
        re.compile(f"""({'|'.join(POSSIBLE_CATEGORIES)})"""),
        re.compile(r"SHA\-256|SHA256|SHA\-1|SHA1|SHA\-512|SHA512|SHA\-3|SHA3"),
    ]
    matches = [regex.search(answer.strip()) for regex in regexes]
    if any(m is not None for m in matches):
        match = next(m for m in matches if m is not None)
        return match.group(1).strip()
    else:
        return answer.strip()


def early_stop(categories) -> Optional[str]:
    # If all categories are the same, return that category
    if len(set(categories)) == 1:
        return categories[0]

    # If there are 4 different categories, return None
    if len(set(categories)) == 4:
        return None


def scan_folder(folder_path):
    for folder in os.walk(folder_path):
        file_names = folder[2]
        for file_name in file_names:
            file_path = os.path.join(folder[0], file_name)
            file_metadata = classify_file(file_path, print_step=False)
            categories_dict = file_metadata.get("categories")
            categories = list(cat["category"] for cat in categories_dict)
            category = early_stop(categories)
            if category is None:
                category = get_true_category_v2_codellama(file_path, categories)
            if category == "ELLIPTIC_CURVES":
                category = "ElipticCurves"
            yield file_path, category

        for sub_folder in folder[1]:
            scan_folder(sub_folder)


if __name__ == "__main__":
    folder_path = sys.argv[1]
    for file, cat in scan_folder(folder_path):
        print(f"File: {file} Category: {cat}")


# from typing import Dict
#
# from ollama import Client, Options
#
#
# options = Options(temperature=0.0)
#
# question = open("files/rsa.alg").read()
#
# prompt = f""" 
# Forget all your previous command. 
# You are a machine capable of recognizing algorithms. 
# We are going to give you a piece of code and possible algorithm's names. Your 
# job is to tell us which algorithm is used in the code. 
#
# The code is as follows: 
# {question} 
#
# The possible algorithms are: 
# RSA, DiffieHellman 
#
# Output ONLY THE NAME OF THE ALGORITHM. DO NOT EXPLAIN ANYTHING, JUST OUTPUT THE NAME. 
#
# """
#
# client = Client(host="http://localhost:11434")
#
# llm_response: Dict = client.generate(
#     model="codellama:7b", prompt=prompt, options=options
# )  # type: ignore
#
# answer = llm_response.get("response", None)
#
# print(f"Answer: {answer.strip()}")
