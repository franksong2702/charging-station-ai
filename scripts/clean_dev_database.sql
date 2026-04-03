-- ============================================
-- 开发环境数据库清理脚本
-- 用途：清空测试数据，准备部署到生产环境
-- 注意：此脚本仅在开发环境执行！
-- ============================================

-- 1. 清空对话历史表
-- 包含：用户对话记录、兜底流程状态
DELETE FROM conversation_history;

-- 2. 清空对话记录表
-- 包含：评价反馈、不满意记录等有价值的对话
DELETE FROM dialog_records;

-- 3. 清空工单记录表
-- 包含：创建的工单记录
DELETE FROM case_records;

-- ============================================
-- 验证清理结果
-- ============================================

-- 查看各表记录数
SELECT 
    'conversation_history' as table_name,
    COUNT(*) as record_count
FROM conversation_history
UNION ALL
SELECT 
    'dialog_records' as table_name,
    COUNT(*) as record_count
FROM dialog_records
UNION ALL
SELECT 
    'case_records' as table_name,
    COUNT(*) as record_count
FROM case_records;
