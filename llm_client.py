import requests
import json
import os

CONFIG_FILE = 'config.json'

def get_llm_config():
    """从配置文件加载LLM和Embedding模型的设置。"""
    if not os.path.exists(CONFIG_FILE):
        return None, None, None, None, None, None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return (
            config.get('base_url'),
            config.get('api_key'),
            config.get('model'),
            config.get('embedding_base_url'),
            config.get('embedding_api_key'),
            config.get('embedding_model')
        )
    except (IOError, json.JSONDecodeError):
        return None, None, None, None, None, None

def get_embedding(text):
    """获取给定文本的embedding向量。"""
    _, _, _, embedding_base_url, embedding_api_key, embedding_model = get_llm_config()
    if not all([embedding_base_url, embedding_api_key, embedding_model]):
        raise ValueError("错误：请先在‘设置’中配置Embedding模型的URL、API Key和名称。")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {embedding_api_key}"
    }
    data = {"input": text, "model": embedding_model}

    try:
        if not embedding_base_url.endswith('/'):
            embedding_base_url += '/'
        api_endpoint = f"{embedding_base_url}v1/embeddings"
        response = requests.post(api_endpoint, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        result = response.json()
        embedding = result['data'][0]['embedding']
        return embedding
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Embedding API 请求失败: {e}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"解析Embedding API响应失败: {e}\n响应内容: {response.text}")

def call_llm(system_prompt, user_prompt):
    """调用LLM API并返回结果。"""
    base_url, api_key, model, _, _, _ = get_llm_config()
    if not all([base_url, api_key, model]):
        raise ValueError("LLM配置不完整，请检查API设置。")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]}

    try:
        if not base_url.endswith('/'):
            base_url += '/'
        api_endpoint = f"{base_url}v1/chat/completions"
        response = requests.post(api_endpoint, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API 请求失败: {e}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"解析API响应失败: {e}\n响应内容: {response.text}")

def generate_prompt(requirement):
    system_prompt = "你是一个提示词工程专家。请根据用户的需求，创建一个高质量、清晰、可复用的提示词模板。模板中应使用双花括号 `{{变量名}}` 来标识变量。"
    return call_llm(system_prompt, requirement)

def optimize_prompt(prompt_content, custom_system_prompt):
    """使用用户自定义的指令优化一个已有的提示词。"""
    return call_llm(custom_system_prompt, prompt_content)
