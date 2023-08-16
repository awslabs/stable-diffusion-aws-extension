
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

if __name__ == "__main__":
    test_dreambooth_create_model()