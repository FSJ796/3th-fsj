"""大模型统一调用封装（T1）：LLMClient.chat(prompt) -> str。

所有 AI 功能（招聘 JD、制度问答、数据点评、浮窗助手）都通过本模块调用，
便于统一控制 Key 校验、超时与失败兜底。API_KEY / BASE_URL / MODEL 只从环境变量读取。
"""
from django.conf import settings
from openai import OpenAI


class AIConfigError(Exception):
    """API Key 未配置时抛出，视图层捕获后返回友好提示而不是 500。"""


class LLMClient:
    """把大模型封装成“会写字的函数”：chat(提示词) -> 文本。"""

    _client = None

    @classmethod
    def is_configured(cls):
        """返回是否已配置 API Key，供页面显示配置状态提醒。"""
        return bool(settings.AI_API_KEY)

    @classmethod
    def _get_client(cls):
        """懒加载 OpenAI 兼容客户端；同一进程只初始化一次，统一 30 秒超时。"""
        if not settings.AI_API_KEY:
            raise AIConfigError(
                '未配置 AI_API_KEY 环境变量，请按方式 A 在 PowerShell 中设置后重启服务'
            )
        if cls._client is None:
            cls._client = OpenAI(
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,  # 换服务只需改 base_url
                timeout=30,  # 网络异常时 30 秒超时，避免请求一直挂起
                max_retries=0,  # 欠费等明确错误不重复请求，尽快启用知识库原文兜底
            )
        return cls._client

    @classmethod
    def chat(cls, prompt, system=None):
        """发送提示词并返回模型生成的文字。

        :param prompt: 用户问题/任务（必需）
        :param system: 系统角色设定（可选），用于给模型定“人设”
        :raises AIConfigError: 未配置 Key；其他异常由视图层统一兜底
        """
        client = cls._get_client()
        messages = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.append({'role': 'user', 'content': prompt})

        resp = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=messages,
            temperature=0.7,  # 随机度：越低越稳定、越高越多样
        )
        return resp.choices[0].message.content
