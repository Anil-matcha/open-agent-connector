"""
AI & LLM Services Provider Suite.
Provides integrations for OpenAI, Anthropic, Perplexity, GroqCloud, Cohere, ElevenLabs, Firecrawl,
Mistral AI, v0, Pinecone, Replicate, Qdrant Cloud, Weaviate, DeepSeek, and Together AI.
"""
from app.providers.builtins.ai.openai import OpenAIProvider
from app.providers.builtins.ai.anthropic import AnthropicProvider
from app.providers.builtins.ai.perplexity import PerplexityProvider
from app.providers.builtins.ai.groqcloud import GroqCloudProvider
from app.providers.builtins.ai.cohere import CohereProvider
from app.providers.builtins.ai.elevenlabs import ElevenLabsProvider
from app.providers.builtins.ai.firecrawl import FirecrawlProvider
from app.providers.builtins.ai.mistral_ai import MistralAIProvider
from app.providers.builtins.ai.v0 import V0Provider
from app.providers.builtins.ai.pinecone import PineconeProvider
from app.providers.builtins.ai.replicate import ReplicateProvider
from app.providers.builtins.ai.qdrant import QdrantProvider
from app.providers.builtins.ai.weaviate import WeaviateProvider
from app.providers.builtins.ai.deepseek import DeepSeekProvider
from app.providers.builtins.ai.together_ai import TogetherAIProvider
from app.providers.builtins.ai.unifapi import UnifapiProvider
from app.providers.builtins.ai.fusion_api import FusionApiProvider
from app.providers.builtins.ai.pixellab import PixelLabProvider
from app.providers.builtins.ai.vapi import VapiProvider
from app.providers.builtins.ai.voiceflow import VoiceflowProvider
from app.providers.builtins.ai.huggingface import HuggingfaceProvider
from app.providers.builtins.ai.chatbotkit import ChatbotkitProvider
from app.providers.builtins.ai.anthropic_admin import AnthropicAdminProvider
from app.providers.builtins.ai.jigsawstack import JigsawstackProvider
from app.providers.builtins.ai.jimeng_ai import JimengAiProvider
from app.providers.builtins.ai.sunoapi import SunoapiProvider
from app.providers.builtins.ai.qianfan import QianfanProvider
from app.providers.builtins.ai.getnote import GetnoteProvider


__all__ = [
    "OpenAIProvider",
    "AnthropicProvider",
    "PerplexityProvider",
    "GroqCloudProvider",
    "CohereProvider",
    "ElevenLabsProvider",
    "FirecrawlProvider",
    "MistralAIProvider",
    "V0Provider",
    "PineconeProvider",
    "ReplicateProvider",
    "QdrantProvider",
    "WeaviateProvider",
    "DeepSeekProvider",
    "TogetherAIProvider",
    "UnifapiProvider",
    "FusionApiProvider",
    "PixelLabProvider",
    "VapiProvider",
    "VoiceflowProvider",
    "HuggingfaceProvider",
    "ChatbotkitProvider",
    "AnthropicAdminProvider",
    "JigsawstackProvider",
    "JimengAiProvider",
    "SunoapiProvider",
    "QianfanProvider",
    "GetnoteProvider",
]

