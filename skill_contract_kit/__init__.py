"""agent-skill-contract-kit: skill-folder contract validator."""
from .parser import parse_frontmatter
from .validator import RULE_TABLE, SkillResult, validate_folder, validate_spec

__all__ = ["parse_frontmatter", "RULE_TABLE", "SkillResult", "validate_folder", "validate_spec"]
__version__ = "1.0.0"
