#!/bin/bash
# sync-skills.sh
# Skills Aggregator 本地同步脚本
# 支持部分就绪状态和静默降级

# 配置
NAS_HOST="${NAS_HOST:-192.168.31.14}"
NAS_PORT="${NAS_PORT:-8080}"
NAS_API="http://${NAS_HOST}:${NAS_PORT}"
LOCAL_SKILLS_DIR="${HOME}/.claude/skills"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
GRAY='\033[0;90m'
NC='\033[0m'

# 静默模式检测（如果不是终端，减少输出）
if [ -t 1 ]; then
    INTERACTIVE=true
else
    INTERACTIVE=false
fi

log() {
    if [ "$INTERACTIVE" = true ]; then
        echo -e "$1"
    fi
}

# 检查 NAS 服务状态（2秒超时，静默降级）
status_response=$(curl -s --connect-timeout 2 "${NAS_API}/api/sync/status" 2>/dev/null)

if [ $? -ne 0 ]; then
    log "${GRAY}(NAS offline, using local cache)${NC}"
    exit 0
fi

state=$(echo "$status_response" | jq -r '.state' 2>/dev/null)
ready_count=$(echo "$status_response" | jq -r '.ready_count // 0' 2>/dev/null)
blocked_count=$(echo "$status_response" | jq -r '.blocked_count // 0' 2>/dev/null)

case "$state" in
    "READY")
        log "${GREEN}✓ 全部就绪，开始同步${NC}"
        SYNC_PATH="ready"
        ;;
    "PARTIAL_READY")
        log "${YELLOW}⚠ 部分就绪 (${ready_count} 可用, ${blocked_count} 待处理)${NC}"
        log "${GRAY}  冲突处理: ${NAS_API}${NC}"
        SYNC_PATH="ready"  # 仅同步 ready 部分
        ;;
    "PULLING"|"ANALYZING"|"MERGING")
        log "${GRAY}(NAS processing: ${state}, using local cache)${NC}"
        exit 0
        ;;
    "IDLE")
        log "${GRAY}(NAS idle, using local cache)${NC}"
        exit 0
        ;;
    *)
        log "${GRAY}(Unknown state: ${state}, using local cache)${NC}"
        exit 0
        ;;
esac

# 创建目标目录
mkdir -p "$LOCAL_SKILLS_DIR"

# rsync 同步（仅同步 ready 目录）
rsync -az --delete \
    "${NAS_HOST}:/path/to/data/output/${SYNC_PATH}/" \
    "$LOCAL_SKILLS_DIR/" 2>/dev/null

if [ $? -eq 0 ]; then
    log "${GREEN}✅ 已同步 ${ready_count} 个 Skills${NC}"
else
    log "${GRAY}(Sync failed, using local cache)${NC}"
fi

exit 0
