
import requests

def test_dreambooth_create_model():
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By

    driver = webdriver.Firefox(executable_path=r'geckodriver')
    driver.get("http://127.0.0.1:7860")
    elem = driver.find_element(By.XPATH, '//*[@id="tabs"]/div[1]/button[7]')
    elem.click()
    elem = driver.find_element(By.XPATH, '//*[@id="component-1370"]/div[1]/button[4]')
    elem.click()
    elem = driver.find_element(By.XPATH, '//*[@id="cloud_db_source_checkpoint_dropdown"]/label/div/div[1]/div/input')
    elem.click()
    driver.close()

def test_img2img_simple_performed(url_img2img, simple_img2img_request):
    assert requests.post(url_img2img, json=simple_img2img_request).status_code == 200


def test_inpainting_masked_performed(url_img2img, simple_img2img_request, mask_basic_image_base64):
    simple_img2img_request["mask"] = mask_basic_image_base64
    assert requests.post(url_img2img, json=simple_img2img_request).status_code == 200


def test_inpainting_with_inverted_masked_performed(url_img2img, simple_img2img_request, mask_basic_image_base64):
    simple_img2img_request["mask"] = mask_basic_image_base64
    simple_img2img_request["inpainting_mask_invert"] = True
    assert requests.post(url_img2img, json=simple_img2img_request).status_code == 200


def test_img2img_sd_upscale_performed(url_img2img, simple_img2img_request):
    simple_img2img_request["script_name"] = "sd upscale"
    simple_img2img_request["script_args"] = ["", 8, "Lanczos", 2.0]
    assert requests.post(url_img2img, json=simple_img2img_request).status_code == 200

if __name__ == "__main__":
    test_dreambooth_create_model()