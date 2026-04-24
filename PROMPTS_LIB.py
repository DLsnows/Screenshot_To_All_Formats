class PROMPTS_LIBRARY:
    def __init__(self):
        self.prompt_text_manager = prompts_manager("text")
        self.prompt_markdown_manager = prompts_manager("markdown")
        self.prompt_html_manager = prompts_manager("html")
        self.prompt_code_manager = prompts_manager("code")
        self.prompt_csv_manager = prompts_manager("csv")
        self.prompt_json_manager = prompts_manager("json")
        self.prompt_latex_manager = prompts_manager("latex")
        self.promptLibraryMap = {"text":self.prompt_text_manager,"markdown":self.prompt_markdown_manager,
                                 "html":self.prompt_html_manager,"code":self.prompt_code_manager,"csv":self.prompt_csv_manager,
                                 "json":self.prompt_json_manager,"latex":self.prompt_latex_manager}

    def get_prompt_from_manager(self,lang:str,format:str):
        manager = self.promptLibraryMap.get(format,None)
        if manager is None:
            raise Exception(f"No prompt found for {format}")
        pmt = manager.get_prompt(lang)
        if pmt is None:
            raise Exception(f"No prompt found for {lang}")
        return pmt

    def update_prompt_from_manager(self,lang:str,format:str,prompt:str):
        manager = self.promptLibraryMap.get(format,None)
        if manager is None:
            self.promptLibraryMap[format] = prompts_manager(format)
        manager.update_lang(lang,prompt)




class prompts_manager:

    def __init__(self,format:str):
        self.promptMap = {}
        self.format = format
    def update_lang(self,lang:str,prompt:str):
        self.promptMap[lang] = prompt
    def get_prompt(self,lang:str):
        return self.promptMap.get(lang,None)

prompts_library = PROMPTS_LIBRARY()
