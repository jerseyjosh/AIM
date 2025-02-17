from typing import Union, Optional
import os

import jinja2

__all__ = ['Email']

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')

def first_sentence(text):
    # Split on period and return the first sentence with a period added back
    parts = text.split('.')
    if parts:
        return parts[0] + '.'
    return ''

class TopImage:
    def __init__(self, image_url: str, image_author: str):
        self.image_url = image_url
        self.image_author = image_author

class Email:
    def __init__(self, template_name: str = 'be_template.html'):
        self.template_name = template_name
        self.template_loader = jinja2.FileSystemLoader(TEMPLATES_DIR)
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters['first_sentence'] = first_sentence
        self.template = self.template_env.get_template(self.template_name)

    def render(self, save_path: Optional[str] = None, **kwargs) -> str:
        res = self.template.render(**kwargs)
        if save_path:
            with open(save_path, "w") as f:
                f.write(res)

if __name__ == "__main__":
    email = Email()
    breakpoint()