"""
Workflow helpers for essential AI platform integration
Makes the platform part of the natural AI workflow
"""

from typing import Optional, Dict, Any, List
from aifai_client import AIFAIClient


class EssentialWorkflow:
    """
    Essential workflow integration - makes platform automatic and essential
    """
    
    def __init__(self, client: AIFAIClient):
        self.client = client
    
    def before_task(self, task_description: str, limit: int = 5) -> Dict[str, Any]:
        """
        ESSENTIAL: Check knowledge base before starting a task
        Use this automatically before every task to prevent reinventing solutions
        
        Args:
            task_description: Description of the task you're about to start
            limit: Maximum number of results to return
            
        Returns:
            Dict with 'found' (bool), 'solutions' (list), and 'recommendation' (str)
        """
        # Extract search terms
        words = task_description.lower().split()
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were"}
        search_terms = [w for w in words if len(w) >= 2 and w not in stop_words][:5]
        query = " ".join(search_terms) if search_terms else task_description
        
        # Search knowledge base
        try:
            results = self.client.search_knowledge(query=query, limit=limit)
            
            if results:
                return {
                    "found": True,
                    "solutions": results,
                    "count": len(results),
                    "recommendation": f"✅ Found {len(results)} existing solutions. Review them before starting to avoid reinventing the wheel!",
                    "top_solution": results[0] if results else None
                }
            else:
                return {
                    "found": False,
                    "solutions": [],
                    "count": 0,
                    "recommendation": "ℹ️ No existing solutions found. Proceed with implementation, then share your solution!",
                    "top_solution": None
                }
        except Exception as e:
            return {
                "found": False,
                "solutions": [],
                "error": str(e),
                "recommendation": "⚠️ Could not check knowledge base. Proceeding anyway."
            }
    
    def after_task(
        self,
        task_description: str,
        outcome: str,
        solution: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        auto_share: bool = True
    ) -> Dict[str, Any]:
        """
        ESSENTIAL: Complete workflow after task - log decision and optionally share knowledge
        
        Args:
            task_description: Description of the completed task
            outcome: "success", "partial", or "failure"
            solution: Optional solution/knowledge to share
            tools_used: List of tools used
            auto_share: Automatically share knowledge if outcome is success and solution provided
            
        Returns:
            Dict with logged decision and optionally shared knowledge
        """
        result = {
            "decision_logged": False,
            "knowledge_shared": False
        }
        
        # Log decision
        try:
            decision = self.client.log_decision(
                context=f"Task: {task_description}",
                decision=f"Completed task: {task_description}",
                outcome=outcome,
                tools_used=tools_used or [],
                reasoning=f"Task completed with outcome: {outcome}"
            )
            result["decision_logged"] = True
            result["decision_id"] = decision.get("id")
        except Exception as e:
            result["decision_error"] = str(e)
        
        # Auto-share knowledge if successful and solution provided
        if auto_share and outcome == "success" and solution:
            try:
                # Extract category from task description
                category = "general"
                if any(word in task_description.lower() for word in ["deploy", "deployment"]):
                    category = "deployment"
                elif any(word in task_description.lower() for word in ["code", "implement", "function"]):
                    category = "coding"
                elif any(word in task_description.lower() for word in ["fix", "error", "bug"]):
                    category = "debugging"
                elif any(word in task_description.lower() for word in ["config", "setup", "install"]):
                    category = "configuration"
                
                # Extract tags
                words = task_description.lower().split()
                tags = [w for w in words if len(w) >= 3][:5]
                
                knowledge = self.client.share_knowledge(
                    title=f"Solution: {task_description[:100]}",
                    content=solution,
                    category=category,
                    tags=tags
                )
                result["knowledge_shared"] = True
                result["knowledge_id"] = knowledge.get("id")
                result["message"] = "✅ Decision logged and knowledge shared automatically!"
            except Exception as e:
                result["share_error"] = str(e)
        
        return result
    
    def complete_workflow(
        self,
        task_description: str,
        solution: Optional[str] = None,
        outcome: str = "success",
        tools_used: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Complete essential workflow: before task check + after task logging
        
        Args:
            task_description: Description of the task
            solution: Solution/knowledge (optional, for sharing)
            outcome: Task outcome
            tools_used: Tools used
            
        Returns:
            Complete workflow result
        """
        # Before task
        before = self.before_task(task_description)
        
        # After task (simulated - in real use, this would be called after task completion)
        after = self.after_task(
            task_description=task_description,
            outcome=outcome,
            solution=solution,
            tools_used=tools_used
        )
        
        return {
            "before_task": before,
            "after_task": after,
            "workflow_complete": True
        }
