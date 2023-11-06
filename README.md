# ormspace 
ORM modules powered by Pydantic for Deta Space.

--- 

### Instructions

The package **ormspace**  will use the deta data key provides as _COLLECTION_KEY_ or will look for _DETA_PROJECT_KEY_ if the 
first is not provided. This way you can set a custom data key or use the project default. The sistem cannot work all is
missing. 

#### the 'modelmap' decorator 
To include the class in the system mapping you must use the 'modelmap' decorator.  With this procedure you will get:
- access to deta space api for read and write your data 
- create special fields for each class:
  - Model.Key 
  - Model.KeyList
  

### Example
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

