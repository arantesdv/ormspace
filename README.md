# ormspace 
ORM modules powered by Pydantic for Deta Space.

--- 

### Instructions
    import datetime
    import asyncio
    from ormspace import model as md

    @md.modelmap
    class Person(md.Model):
        first_name: str 
        last_name: str 
        birth_date: datetime.date

    @md.modelmap
    class Patient(md.Model):
        person_key: Person.Key


    async def main():
        await Patient.update_references_context()
        for item in await Patient.sorted_instances_list():
            print(item)

    asyncio.run(main())

