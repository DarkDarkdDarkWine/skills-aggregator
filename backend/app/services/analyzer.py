from typing import Dict, List, Any, Optional
import json
import hashlib
import logging
from pathlib import Path

from ..config import config
from .ai_provider import get_ai_provider

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI 分析引擎"""

    # 分析提示词模板
    SINGLE_ANALYZE_PROMPT = """你是一个 Claude Code / OpenCode Skills 分析专家。

请分析以下 Skill 的内容，提取关键信息：

<skill>
来源仓库：{{repo_name}}
Skill 名称：{{skill_name}}
文件路径：{{file_path}}

SKILL.md 内容：
```
{{skill_md_content}}
```

附带文件列表：
{{file_list}}
</skill>

请输出 JSON 格式的分析结果：

{{analysis_format}}

评分标准：
- 90-100：文档完整、有示例、有错误处理、结构清晰
- 70-89：基本完整，有小问题
- 50-69：可用但有明显不足
- 0-49：质量较差，缺失关键内容

只输出 JSON，不要其他内容。
"""

    CONFLICT_COMPARE_PROMPT = """你是一个 Claude Code / OpenCode Skills 分析专家。

以下是来自不同仓库的同名 Skill，请对比分析并给出推荐：

<skills>
{{#each skills}}
## 来源 {{index}}：{{repo_name}}（优先级：{{priority}}）

SKILL.md 内容：
```
{{skill_md_content}}
```

附带文件：{{file_list}}

---
{{/each}}
</skills>

请分析并输出 JSON：

{{comparison_format}}

决策建议原则：
- 如果某个版本明显更完整、质量更高，推荐 choose_one
- 如果各有优劣且互补，推荐 merge
- 如果功能有差异用户可能都需要，推荐 keep_all（会重命名区分）

只输出 JSON，不要其他内容。
"""

    SIMILAR_CLUSTER_PROMPT = """你是一个 Claude Code / OpenCode Skills 分析专家。

以下是从多个仓库收集的所有 Skills 摘要信息，请识别功能相似或重叠的 Skills 并分组：

<all_skills>
{{#each skills}}
- 名称：{{name}}
  仓库：{{repo}}
  摘要：{{summary}}
  标签：{{tags}}
  触发词：{{triggers}}

{{/each}}
</all_skills>

请识别功能相似的 Skills 并分组，输出 JSON：

{{cluster_format}}

判断标准：
- 触发词高度重叠（>50%）→ 很可能相似
- 标签相同 + 摘要描述相似 → 可能相似
- 仅仅是同一领域（如都和 git 相关）但功能不同 → 不算相似
- 一个是另一个的子集 → 算相似

只输出 JSON，不要其他内容。
"""

    MERGE_PROMPT = """你是一个 Claude Code / OpenCode Skills 专家，擅长编写高质量的 SKILL.md。

以下是几个功能相似的 Skills，用户希望将它们合并为一个更强大的版本：

<skills_to_merge>
{{#each skills}}
## {{repo}}/{{name}}

SKILL.md：
```
{{skill_md_content}}
```

附带脚本：
{{#each scripts}}
文件：{{filename}}
```
{{content}}
```
{{/each}}

---
{{/each}}
</skills_to_merge>

{{#if renaming_history}}
<renaming_history>
以下是历史合并中的文件重命名记录，请参考保持命名一致性：
{{#each renaming_history}}
- 原文件: {{original_filename}} (来自 {{source_repo}})
  → 重命名为: {{assigned_filename}}
  理由: {{reasoning}}
{{/each}}
</renaming_history>
{{/if}}

请生成合并后的 Skill，要求：

1. SKILL.md 规范：
   - 必须有 YAML frontmatter（name, description）
   - 整合所有版本的优点和使用场景
   - 结构清晰，易于理解
   - 保持简洁，避免冗余

2. 脚本处理：
   - 如果多个脚本功能重复，合并为一个
   - 如果功能互补，都保留
   - 确保脚本之间没有命名冲突
   - 参考历史重命名记录，保持命名一致性

输出格式：

{{merge_format}}

只输出 JSON，不要其他内容。
"""

    def __init__(self):
        self.ai = get_ai_provider()
        self.analysis_cache_dir = Path(config.storage.analysis_cache_dir)
        self.analysis_cache_dir.mkdir(parents=True, exist_ok=True)

    async def analyze_skill(
        self,
        repo_name: str,
        skill_name: str,
        skill_content: str,
        file_list: List[str],
    ) -> Dict[str, Any]:
        """分析单个 Skill"""
        # 检查缓存
        cache_key = hashlib.md5(
            f"{repo_name}:{skill_name}:{skill_content}".encode()
        ).hexdigest()
        cache_path = self.analysis_cache_dir / f"{cache_key}.json"

        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text())
            except Exception:
                pass

        # 构建提示词
        prompt = (
            self.SINGLE_ANALYZE_PROMPT.replace("{{repo_name}}", repo_name)
            .replace("{{skill_name}}", skill_name)
            .replace("{{file_path}}", f"skills/{skill_name}")
            .replace("{{skill_md_content}}", skill_content)
            .replace("{{file_list}}", "\n".join(file_list) if file_list else "无")
            .replace("{{analysis_format}}", self._get_analysis_format())
        )

        try:
            result = await self.ai.analyze(prompt)

            # 缓存结果
            cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

            return result
        except Exception as e:
            logger.error(f"Failed to analyze skill: {e}")
            raise

    async def compare_skills(
        self,
        skills: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """对比同名 Skills"""
        # 构建提示词
        skills_html = ""
        for i, skill in enumerate(skills):
            skills_html += f"""## 来源 {i + 1}：{skill["repo_name"]}（优先级：{skill["priority"]}）

SKILL.md 内容：
```
{skill["content"]}
```

附带文件：{", ".join([s["name"] for s in skill["scripts"]])}

---

"""

        prompt = self.CONFLICT_COMPARE_PROMPT.replace(
            "{{skills}}", skills_html
        ).replace("{{comparison_format}}", self._get_comparison_format())

        return await self.ai.analyze(prompt)

    async def cluster_skills(
        self,
        skills: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """聚类相似的 Skills"""
        skills_html = ""
        for skill in skills:
            skills_html += f"""- 名称：{skill["name"]}
  仓库：{skill["repo_name"]}
  摘要：{skill.get("summary", "")}
  标签：{", ".join(skill.get("tags", []))}
  触发词：{", ".join(skill.get("triggers", []))}

"""

        prompt = self.SIMILAR_CLUSTER_PROMPT.replace("{{skills}}", skills_html).replace(
            "{{cluster_format}}", self._get_cluster_format()
        )

        return await self.ai.analyze(prompt)

    async def merge_skills(
        self,
        skills: List[Dict[str, Any]],
        renaming_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """合并 Skills"""
        skills_html = ""
        for skill in skills:
            scripts_html = ""
            for script in skill.get("scripts", []):
                scripts_html += f"""文件：{script["name"]}}}
```
{script.get("content", "")}
```
"""

            skills_html += f"""## {skill["repo_name"]}/{skill["name"]}

SKILL.md：
```
{skill["content"]}
```

附带脚本：
{scripts_html}

---
"""

        renaming_history_html = ""
        if renaming_history:
            for record in renaming_history:
                renaming_history_html += f"""- 原文件: {record["original_filename"]} (来自 {record["source_repo"]})
  → 重命名为: {record["assigned_filename"]}
  理由: {record["reasoning"]}
"""

        prompt = (
            self.MERGE_PROMPT.replace("{{skills}}", skills_html)
            .replace(
                "{{renaming_history}}",
                f"<renaming_history>\n{renaming_history_html}\n</renaming_history>"
                if renaming_history
                else "",
            )
            .replace("{{merge_format}}", self._get_merge_format())
        )

        return await self.ai.analyze(prompt)

    def _get_analysis_format(self) -> str:
        """获取分析结果格式"""
        return """
{
  "name": "skill 名称",
  "summary": "一句话描述这个 skill 的核心功能（20字以内）",
  "description": "详细功能描述（100字以内）",
  "use_cases": ["使用场景1", "使用场景2"],
  "triggers": ["触发关键词1", "触发关键词2"],
  "dependencies": {
    "scripts": ["依赖的脚本文件"],
    "external": ["外部依赖，如 python 包、npm 包等"]
  },
  "quality_score": 0-100,
  "quality_issues": ["问题1", "问题2"],
  "tags": ["标签1", "标签2"]
}
"""

    def _get_comparison_format(self) -> str:
        """获取对比结果格式"""
        return """
{
  "skill_name": "skill 名称",
  "comparison": [
    {
      "repo": "仓库名",
      "strengths": ["优点1", "优点2"],
      "weaknesses": ["缺点1", "缺点2"],
      "completeness": 0-100,
      "quality": 0-100
    }
  ],
  "recommendation": {
    "action": "choose_one | merge | keep_all",
    "chosen": "推荐的仓库名（如果 action 是 choose_one）",
    "reason": "推荐理由（50字以内）",
    "merge_suggestion": "如果建议合并，简述合并思路（100字以内）"
  }
}
"""

    def _get_cluster_format(self) -> str:
        """获取聚类结果格式"""
        return """
{
  "similar_groups": [
    {
      "group_name": "功能组名称",
      "description": "这组 skills 的共同功能",
      "skills": [
        {"name": "skill1", "repo": "repo-a"},
        {"name": "skill2", "repo": "repo-b"}
      ],
      "similarity_reason": "为什么认为它们相似",
      "recommendation": {
        "action": "merge | choose_best | keep_all",
        "reason": "建议理由"
      }
    }
  ],
  "unique_skills": [
    {"name": "独立skill", "repo": "repo-x"}
  ]
}
"""

    def _get_merge_format(self) -> str:
        """获取合并结果格式"""
        return """
{
  "merged_skill": {
    "name": "合并后的名称",
    "skill_md": "完整的 SKILL.md 内容（直接可用）",
    "scripts": [
      {"filename": "xxx.py", "content": "完整内容"}
    ],
    "renaming_records": [
      {
        "original_filename": "原文件名",
        "assigned_filename": "新文件名",
        "source_repo": "来源仓库",
        "reasoning": "重命名理由"
      }
    ],
    "kept_from": {
      "仓库A": ["保留的内容描述"],
      "仓库B": ["保留的内容描述"]
    },
    "improvements": ["相比原版本的改进点"]
  }
}
"""


# 创建全局实例
_analyzer: Optional[AIAnalyzer] = None


def get_analyzer() -> AIAnalyzer:
    """获取 AI Analyzer 实例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = AIAnalyzer()
    return _analyzer
