"""Phase 7 数据分析路由。

GET  /api/analytics/report    -> 聚合指标（图表/卡片数据源，无 AI）
POST /api/analytics/summary   -> 生成 AI 学习报告文字并落库 ai_analysis
"""
import json

from flask import Blueprint, request, jsonify
from app.extensions import db
from utils.jwt_utils import login_required
from services.analytics_service import build_report
from ai.service import AIService
from models.analysis import AIAnalysis

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/report', methods=['GET'])
@login_required
def report(current_user):
    range_type = request.args.get('range', 'week')
    start = request.args.get('start')
    end = request.args.get('end')
    if range_type not in ('day', 'week', 'month', 'all'):
        return jsonify({'code': 400, 'message': '非法 range，应为 day/week/month/all'}), 400
    data = build_report(current_user.id, range_type, start, end)
    return jsonify({'code': 200, 'data': data})


@analytics_bp.route('/summary', methods=['POST'])
@login_required
def summary(current_user):
    body = request.get_json(silent=True) or {}
    range_type = body.get('range', 'week')
    start = body.get('start')
    end = body.get('end')

    metrics = build_report(current_user.id, range_type, start, end)
    result = AIService().learning_report(metrics)

    # 落库，便于回看/分享
    rec = AIAnalysis(
        user_id=current_user.id,
        analysis_type='learning_report',
        input_data=json.dumps(metrics, ensure_ascii=False),
        output_data=result['text'],
    )
    db.session.add(rec)
    db.session.commit()

    return jsonify({
        'code': 200,
        'data': {
            'text': result['text'],
            'source': result['source'],
            'analysis_id': rec.id,
            'range': range_type,
        },
    })
