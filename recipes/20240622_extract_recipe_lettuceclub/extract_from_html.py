import requests, tiktoken
from operator import itemgetter
from bs4 import BeautifulSoup
from langchain_community.document_loaders.html import UnstructuredHTMLLoader
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from recipe_schema import RecipeCreate, RecipeWithURL

def load_doc(url):
    response = requests.get(url)
    with open('temp.html','w') as f:
        f.write(response.text)
    loader = UnstructuredHTMLLoader("temp.html")
    docs = loader.load()
    content = docs[0].page_content.replace('\n\n', '\n')
    return content

recipe_create_tool = convert_to_openai_function(RecipeCreate)

system_recipe_extract = '''\
You are a recipe researcher. user input recipe text.
You should output recipe json. (lang: ja)
'''

functions = [recipe_create_tool]
model = ChatOpenAI(model='gpt-3.5-turbo', temperature=0., streaming=True)
model_with_func = model.bind_functions(functions)

chat_template_recipe = ChatPromptTemplate.from_messages([
    SystemMessage(content=system_recipe_extract),
    HumanMessagePromptTemplate.from_template('{web_text}'),
])

recipe_chain = chat_template_recipe | model_with_func | JsonOutputFunctionsParser()

## extract images
def extract_images(url):
    headers = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
    }
    response = requests.request("GET", url, headers=headers)
    data = BeautifulSoup(response.text, 'html.parser')
    # find all with the image tag
    images = data.find_all('img', src=True)
    return images

system_images_extract = '''\
Which is the main image of this recipe?
Please determine from the ALT text and URL.
Provide full url. Only URL is needed.
'''

model = ChatOpenAI(model='gpt-3.5-turbo', temperature=0., streaming=True)
chat_template_images = ChatPromptTemplate.from_messages([
    SystemMessage(content=system_images_extract),
    HumanMessagePromptTemplate.from_template('## Recipe\n{recipe}'),
    HumanMessagePromptTemplate.from_template('## URL\n{url}'),
    HumanMessagePromptTemplate.from_template('## Images\n{images}'),
])

images_chain = chat_template_images | model

chain = {
    'url': RunnablePassthrough(),
    'recipe': RunnablePassthrough() | RunnableLambda(load_doc) | {'web_text': RunnablePassthrough()} | recipe_chain,
}\
| RunnablePassthrough() \
| {
    'url': itemgetter('url'),
    'recipe': itemgetter('recipe'),
    'image_url': {
        'url': itemgetter('url'),
        'recipe': itemgetter('recipe') | RunnableLambda(lambda x: str(x)),
        'images': itemgetter('url') | RunnableLambda(extract_images) | RunnableLambda(lambda x: str(x))
    } | images_chain | RunnableLambda(lambda x: x.content) # type: ignore
} | RunnableLambda(
    lambda x: RecipeWithURL(
        url=x['url'],image_url=x['image_url'], **x['recipe']# type: ignore
    )
)