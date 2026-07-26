import os

from flask import Blueprint, request, jsonify
from models.material import Material
from app.extensions import db
from utils.jwt_utils import login_required
from ai.rag import RAGService

material_bp = Blueprint('material', __name__)


@material_bp.route('', methods=['POST'])
@login_required
def upload_material(current_user):
    """上传复习资料（RAG 素材）：支持 .txt/.md 文本，或 .pdf（提取文本层）。"""
    title = (request.form.get('title') or '').strip()
    content = (request.form.get('content') or '').strip()
    source = Material.SOURCE_TEXT

    # 文件上传优先（.txt/.md/.pdf）
    if 'file' in request.files and request.files['file'].filename:
        f = request.files['file']
        filename = getattr(f, 'filename', '') or ''
        ext = os.path.splitext(filename)[1].lower()
        if ext in ('.txt', '.md'):
            content = f.read().decode('utf-8', errors='ignore')
            source = Material.SOURCE_TEXT
        elif ext == '.pdf':
            try:
                from parser.pdf_parser import extract_pdf_text
                content = extract_pdf_text(f)
            except ImportError:
                return jsonify({'code': 500, 'message': 'PDF 解析依赖未安装，请先 pip install pdfminer.six'}), 500
            source = Material.SOURCE_PDF
        else:
            return jsonify({'code': 400, 'message': '仅支持 .txt / .md / .pdf'}), 400
        if not title:
            title = os.path.splitext(filename)[0]

    if not title:
        return jsonify({'code': 400, 'message': '请填写标题'}), 400
    if not content.strip():
        return jsonify({'code': 400, 'message': '资料内容为空'}), 400

    mat = Material(
        user_id=current_user.id,
        title=title[:128],
        content=content,
        source=source,
    )
    db.session.add(mat)
    db.session.commit()
    return jsonify({'code': 200, 'message': '资料已保存', 'data': mat.to_dict()}), 201


@material_bp.route('', methods=['GET'])
@login_required
def list_materials(current_user):
    """列出当前用户的资料。"""
    mats = Material.query.filter_by(user_id=current_user.id).order_by(Material.create_time.desc()).all()
    return jsonify({'code': 200, 'data': [m.to_dict() for m in mats]})


@material_bp.route('/<int:material_id>', methods=['DELETE'])
@login_required
def delete_material(current_user, material_id):
    """删除一条资料。"""
    mat = Material.query.filter_by(id=material_id, user_id=current_user.id).first()
    if not mat:
        return jsonify({'code': 404, 'message': '资料不存在'}), 404
    db.session.delete(mat)
    db.session.commit()
    return jsonify({'code': 200, 'message': '已删除'})


@material_bp.route('/match', methods=['POST'])
@login_required
def match_material(current_user):
    """根据查询（任务标题/内容）检索相关复习资料（U3 RAG 关键词 MVP）。"""
    data = request.get_json(silent=True) or {}
    query = (data.get('query') or data.get('content') or '').strip()
    if not query:
        return jsonify({'code': 400, 'message': '请提供 query 或 content'}), 400

    mats = Material.query.filter_by(user_id=current_user.id).all()
    results = RAGService.keyword_retrieve(query, mats, top_k=int(data.get('top_k', 3)))
    return jsonify({'code': 200, 'data': results})
