"""
Base Agent Module
================
Foundation for all AI agents with:
- LangChain integration
- Tool usage
- Memory management
- Error handling
- Performance tracking

Author: Production Team
Version: 1.0.0
"""

from typing import Any, Dict, List, Optional, Type
from abc import ABC, abstractmethod
from datetime import datetime
import asyncio
import time

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.tools import BaseTool
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage

from src.core.config import settings
from src.core.logging import get_logger
from src.core.exceptions import (
    AgentError,
    AgentExecutionError,
    AgentTimeoutError
)


logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.
    
    Features:
    - LLM integration
    - Tool management
    - Memory
    - Error handling
    - Performance tracking
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        tools: Optional[List[BaseTool]] = None,
        memory: bool = True,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_iterations: int = 10,
        timeout: int = 300
    ):
        """
        Initialize base agent.
        
        Args:
            name: Agent name
            description: Agent description
            tools: List of tools available to agent
            memory: Enable conversation memory
            model: LLM model to use
            temperature: LLM temperature
            max_iterations: Maximum agent iterations
            timeout: Execution timeout in seconds
        """
        self.name = name
        self.description = description
        self.tools = tools or []
        self.model_name = model or settings.AGENT_MODEL
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.timeout = timeout
        
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # Initialize memory
        self.memory = None
        if memory:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        
        # Initialize agent executor
        self.agent_executor = self._create_agent_executor()
        
        logger.info(
            f"Initialized agent: {self.name}",
            extra={
                "agent": self.name,
                "model": self.model_name,
                "num_tools": len(self.tools),
                "has_memory": memory
            }
        )
    
    def _initialize_llm(self) -> ChatOpenAI:
        """
        Initialize language model.
        
        Returns:
            ChatOpenAI: Configured LLM instance
        """
        try:
            llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=settings.AGENT_MAX_TOKENS,
                api_key=settings.OPENAI_API_KEY,
            )
            
            logger.debug(
                f"LLM initialized for agent: {self.name}",
                extra={"model": self.model_name}
            )
            
            return llm
        
        except Exception as e:
            logger.error(
                f"Failed to initialize LLM for agent: {self.name}",
                error=e
            )
            raise AgentError(
                message=f"Failed to initialize LLM for agent {self.name}",
                details={"error": str(e)}
            )
    
    def _create_agent_executor(self) -> AgentExecutor:
        """
        Create agent executor with tools and memory.
        
        Returns:
            AgentExecutor: Configured agent executor
        """
        try:
            # Create system prompt
            system_prompt = self._get_system_prompt()
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Create agent
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            
            # Create executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=self.memory,
                max_iterations=self.max_iterations,
                verbose=settings.DEBUG,
                return_intermediate_steps=True,
            )
            
            return agent_executor
        
        except Exception as e:
            logger.error(
                f"Failed to create agent executor for: {self.name}",
                error=e
            )
            raise AgentError(
                message=f"Failed to create agent executor for {self.name}",
                details={"error": str(e)}
            )
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """
        Get agent system prompt.
        
        Returns:
            str: System prompt
            
        Note: Must be implemented by subclasses
        """
        pass
    
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute agent task with timeout.
        
        Args:
            task: Task description
            context: Additional context
            
        Returns:
            dict: Execution result with metadata
            
        Raises:
            AgentExecutionError: If execution fails
            AgentTimeoutError: If execution times out
        """
        start_time = time.time()
        
        logger.info(
            f"Starting agent execution: {self.name}",
            extra={
                "agent": self.name,
                "task": task[:100],  # Truncate for logging
                "has_context": context is not None
            }
        )
        
        try:
            # Prepare input
            agent_input = {
                "input": task,
                **(context or {})
            }
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_task(agent_input),
                timeout=self.timeout
            )
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Prepare response
            response = {
                "agent": self.name,
                "task": task,
                "result": result.get("output"),
                "intermediate_steps": result.get("intermediate_steps", []),
                "execution_time_seconds": round(execution_time, 4),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
            logger.info(
                f"Agent execution completed: {self.name}",
                extra={
                    "agent": self.name,
                    "execution_time_seconds": execution_time,
                    "status": "completed"
                }
            )
            
            return response
        
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            
            logger.error(
                f"Agent execution timeout: {self.name}",
                extra={
                    "agent": self.name,
                    "timeout_seconds": self.timeout,
                    "execution_time_seconds": execution_time
                }
            )
            
            raise AgentTimeoutError(
                agent_name=self.name,
                timeout=self.timeout,
                details={
                    "task": task,
                    "execution_time_seconds": execution_time
                }
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(
                f"Agent execution failed: {self.name}",
                error=e,
                extra={
                    "agent": self.name,
                    "execution_time_seconds": execution_time
                }
            )
            
            raise AgentExecutionError(
                agent_name=self.name,
                details={
                    "task": task,
                    "error": str(e),
                    "execution_time_seconds": execution_time
                }
            )
    
    async def _execute_task(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent task asynchronously.
        
        Args:
            agent_input: Agent input dictionary
            
        Returns:
            dict: Agent execution result
        """
        # Run in executor since LangChain is not fully async
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.agent_executor.invoke,
            agent_input
        )
        
        return result
    
    def add_tool(self, tool: BaseTool) -> None:
        """
        Add tool to agent.
        
        Args:
            tool: Tool to add
        """
        self.tools.append(tool)
        # Recreate agent executor with new tool
        self.agent_executor = self._create_agent_executor()
        
        logger.info(
            f"Tool added to agent: {self.name}",
            extra={"agent": self.name, "tool": tool.name}
        )
    
    def clear_memory(self) -> None:
        """Clear agent memory."""
        if self.memory:
            self.memory.clear()
            logger.debug(f"Memory cleared for agent: {self.name}")
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get agent information.
        
        Returns:
            dict: Agent metadata
        """
        return {
            "name": self.name,
            "description": self.description,
            "model": self.model_name,
            "temperature": self.temperature,
            "num_tools": len(self.tools),
            "tools": [tool.name for tool in self.tools],
            "max_iterations": self.max_iterations,
            "timeout": self.timeout,
            "has_memory": self.memory is not None
        }


# Export
__all__ = ["BaseAgent"]