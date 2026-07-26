import logging

from flask import Blueprint, request, jsonify
from utils.jwt_utils import login_required
from ai import rag_service, ai_service

logger = logging.getLogger(__name__)

rag_bp = Blueprint('rag', __name__)


@rag_bp.route('/query', methods=['POST'])
@login_required
def rag_query(current_user):
    """基于用户资料库的 RAG 问答：检索相关资料 + DeepSeek 生成回答。"""
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return jsonify({'code': 400, 'message': '请提供 question'}), 400
    top_k = data.get('top_k')

    try:
        result = ai_service.rag_answer(current_user.id, question, top_k=top_k)
    except Exception as e:
        logger.error(f'RAG 问答失败: {e}')
        return jsonify({'code': 500, 'message': f'RAG 问答失败: {str(e)}'}), 500

    return jsonify({'code': 200, 'data': result})


@rag_bp.route('/index', methods=['POST'])
@login_required
def rag_index(current_user):
    """重建当前用户的资料向量索引（上传/删除资料后会自动失效，通常无需手动调用）。"""
    try:
        entry = rag_service.rebuild(current_user.id)
    except Exception as e:
        logger.error(f'RAG 索引重建失败: {e}')
        return jsonify({'code': 500, 'message': f'索引重建失败: {str(e)}'}), 500
    return jsonify({
        'code': 200,
        'message': '索引已重建',
        'data': {'chunk_count': len(entry['chunks']), 'mode': entry['mode']},
    })


@rag_bp.route('/status', methods=['GET'])
@login_required
def rag_status(current_user):
    """查询当前用户索引状态（是否已建、分块数、向量/关键词模式、模型名）。"""
    return jsonify({'code': 200, 'data': rag_service.status(current_user.id)})
