from abc import ABC, abstractmethod


class Job(ABC):
    name: str

    @abstractmethod
    async def run(self) -> None:
        pass
