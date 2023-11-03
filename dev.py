import asyncio

from spacemodel import keymodel as km


@km.model_map
class Person(km.KeyModel):
    EXIST_QUERY = 'fname'
    fname: str
    lname: str
    
@km.model_map
class Patient(km.KeyModel):
    EXIST_QUERY = 'person_key'
    person_key: km.Annotated[km.Key, km.MetaData(tables=['Person'], item_name='person')]


async def read():
    await Patient.set_context_data()
    for k in Patient.get_context_data():
        print(Patient.get_context_instance(k))
        


if __name__ == '__main__':
    asyncio.run(read())