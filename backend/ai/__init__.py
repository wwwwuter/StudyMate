from ai.deepseek_client import DeepSeekClient
from ai.service import AIService
from ai.rag import RAGService

# 全局共享实例：保证各路由（material / rag）使用同一 RAGService 缓存
rag_service = RAGService()
ai_service = AIService(rag=rag_service)

__all__ = ['DeepSeekClient', 'AIService', 'RAGService', 'rag_service', 'ai_service']
