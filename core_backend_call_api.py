from pathlib import Path
from openai import OpenAI
import pyperclip
import base64
import os
from concurrent.futures import ThreadPoolExecutor
from Screenshot_To_All_Formats.PROMPTS_LIB import prompts_library
import Screenshot_To_All_Formats.prompt_setting as prompt_setting

def ocr(client,imagePath:str,model:str,prompt:str,max_token):
    ext = Path(imagePath).suffix.lower()
    mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
    mime_type = mime_map.get(ext, 'image/png')  # 默认 PNG
    with open(imagePath, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        chat_completion = client.chat.completions.create(
            model=model,
            max_tokens=max_token,
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
        )
    #print("OCR finished")
    return chat_completion.choices[0].message.content

def call_api_for_ocr(copy_to_clipboard: bool, input_image_path: str, language: str, format: str,
                     api: str, url: str, model: str, output_path: str, max_token: int = 30000):
    client = OpenAI(
        api_key=api,
        base_url=url,
    )
    file_name_end_map = {'markdown': '.md', 'html': '.html', 'csv': '.csv', 'json': '.json', 'latex': '.tex'}
    file_name_end = file_name_end_map.get(format, '.txt')
    prompt = prompts_library.get_prompt_from_manager(language, format)

    # 获取所有图片文件名（仅文件名，不包含路径）
    image_files = os.listdir(input_image_path)

    # 计算并发数：图片数量，上限 50
    concurrency = min(len(image_files), 50)

    # 定义每个图片的处理任务
    def process_image(image_name: str) -> str:
        image_path = os.path.join(input_image_path, image_name)
        # 调用 OCR
        return ocr(client, image_path, model, prompt, max_token)

    # 并发处理所有图片，保持顺序
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # executor.map 会按输入顺序返回结果，即使各任务完成时间不同
        content_list = list(executor.map(process_image, image_files))

    # 为每个图片写出单独的结果文件
    for image_name, content in zip(image_files, content_list):
        output_file_path = os.path.join(output_path, image_name + file_name_end)
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(content)

    # 所有结果合并写入 all_in_one.txt
    all_in_one_path = os.path.join(output_path, 'all_in_one'+file_name_end)
    with open(all_in_one_path, "w", encoding="utf-8") as f:
        f.write('\n\n\n'.join(content_list))

    # 复制最后一个图片的结果到剪贴板
    if copy_to_clipboard and content_list:
        # 注意：原单线程代码使用的是 content[-1]（字符串最后字符），此处修正为 content_list[-1]
        pyperclip.copy(content_list[-1])