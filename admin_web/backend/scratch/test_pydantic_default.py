from pydantic import BaseModel, Field
from datetime import datetime

class MockORM:
    def __init__(self):
        self.id = 1
        self.name = "Spring 2026"

class SemesterOutTest(BaseModel):
    id: int
    name: str
    server_time: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

obj = MockORM()
parsed = SemesterOutTest.model_validate(obj)
print("Parsed ID:", parsed.id)
print("Parsed Name:", parsed.name)
print("Parsed Server Time:", parsed.server_time)
