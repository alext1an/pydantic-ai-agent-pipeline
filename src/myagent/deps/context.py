from dataclasses import dataclass

@dataclass
class AgentDeps:
    '''
    Agent dependencies 
    This class stores the agent's runtime context information,
    including the user name, working directory, and other relevant context information.
    '''
    user_name: str
    user_tier: str = "standard"

