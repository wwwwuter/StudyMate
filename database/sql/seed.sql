-- 测试数据（仅用于开发环境）

USE studymate;

-- 插入测试用户
INSERT INTO users (openid, nickname, avatar) VALUES
('test_openid_001', '测试用户', 'https://example.com/avatar.png');

-- 插入测试任务
INSERT INTO study_tasks (user_id, date, subject, content, start_time, end_time, status) VALUES
(1, '2026-07-20', '数学', '高数强化-极限与导数应用', '08:30', '11:30', 'done'),
(1, '2026-07-20', '英语', '考研英语阅读真题2010-T1', '14:00', '16:00', 'done'),
(1, '2026-07-20', '408', '数据结构-树与二叉树遍历', '19:00', '21:00', 'pending'),
(1, '2026-07-21', '数学', '高数强化-微分中值定理', '08:30', '11:30', 'pending'),
(1, '2026-07-21', '英语', '考研英语阅读真题2010-T2', '14:00', '16:00', 'pending'),
(1, '2026-07-21', '政治', '马原-唯物辩证法', '19:00', '21:00', 'pending');