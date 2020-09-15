from botocore.exceptions import ClientError
from PIL import Image
from urllib import parse
from os import environ
from subprocess import run
import boto3
from typing import List, Tuple, Optional
import base64
import io
import os

s3_bucket_name: str = "image.grabfood.com"
s3_client = boto3.client("s3")

webp_content_type = "image/webp"

def lambda_handler(event: dict, context) -> dict:
    print("0 - start lambda handler", event)
    record: dict = event["Records"][0]["cf"]
    request: dict = record["request"]
    response: dict = record["response"]

    print("start lambda handler", response["status"])

    if int(response["status"]) == 200:
        return response
   
    target_width: int = 0
    target_height: int = 0
    target_quality: int = 80

    s3_object_key: str = request["uri"][1:]
    s3_object_key_split: List[str] = s3_object_key.split("/")

    ## https://d3nk6pcgpmbqy2.cloudfront.net/item/4-CZNVTK2ZVUAWJA-CZNVTK4TFA3CAT/photos/3bdd0da46956405c83422969cf8b7ddd_1599282750305723140.jpeg (
    ## https://d1sag4ddilekf6.cloudfront.net/compressed_webp/items/6-CY6KUEDEG8NKSE-CY6KUE31T8DWAX/photo/menueditor_items_ba17977dff0e4f42ab32a77a619ac778_1599834118337126516.webp
    if len(s3_object_key_split) == 5 and s3_object_key_split[0] == "compressed_webp" and s3_object_key_split[1] == "items" and s3_object_key_split[3] == "photo":
        original_object_arr = ["item", s3_object_key_split[2], "photos", s3_object_key_split[4]]
        original_object_key: str = "/".join(original_object_arr)
        target_width = 300
        target_height = 300
    else: 
        print("invalid url, can't progress")
        return response

    try:
        original_s3_response, original_file_extension = get_original_file(bucket_name=s3_bucket_name, key=parse.unquote(original_object_key))
    except ClientError as e:
        raise e
    if original_file_extension == "":
        print("can't find original image")
        return response

    dest_file_name = s3_object_key_split[4]
    dest_file_path = "/tmp/" + dest_file_name
    original_file_split = s3_object_key_split[4].split(".")
    original_file_split[-1] = original_file_extension
    original_file_name = ".".join(original_file_split)
    source_file_path: str = "/tmp/" + original_file_name 

    # import original image
    original_image: Image = Image.open(original_s3_response["Body"])
    original_image.save(source_file_path)
    original_image.close()

    convertCommandParameters = ["./cwebp", "-q", str(target_quality), "-quiet"]
    if target_width > 0 and target_height > 0:
        convertCommandParameters.append("-resize")
        convertCommandParameters.append(str(target_width))
        convertCommandParameters.append(str(target_height))

    convertCommandParameters.append(source_file_path)
    convertCommandParameters.append("-o")
    convertCommandParameters.append(dest_file_path)
    run(convertCommandParameters)

    webp_file_handler = open(dest_file_path, "rb")
    result_data: bytes = webp_file_handler.read()
    result: str = base64.standard_b64encode(result_data).decode()

    # remove files
    os.remove(source_file_path)
    os.remove(dest_file_path)

    # store compressed img
    try:
        compressed_s3_response = s3_client.put_object(
            Bucket=s3_bucket_name,
            Key=parse.unquote(s3_object_key),
            ContentType=webp_content_type,
            Body=result_data,
        )
    except ClientError as e:
        raise e

    response["status"] = 200
    response["statusDescription"] = "OK"
    response["body"] = result
    response["bodyEncoding"] = "base64"
    response["headers"]["content-type"] = [
        {"key": "Content-Type", "value": webp_content_type}
    ]

    return response

def get_original_file(bucket_name: str, key: str):
    valid_file_extensions = ["jpeg", "jpg", "png", "gif"]
    key_split = key.split(".")

    file_extension_value = ""
    s3_response = ""
    for file_extension in valid_file_extensions:
        try:
            key_split[-1] = file_extension
            updated_key = ".".join(key_split)
            print("get_object", bucket_name, updated_key)
            s3_response = s3_client.get_object(Bucket=bucket_name, Key=updated_key)
            file_extension_value = file_extension
            break
        except ClientError as e:
            file_extension_value = ""
            continue
    return s3_response, file_extension_value

