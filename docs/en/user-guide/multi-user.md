# Configure API and Multiple Users.

### 1. After the deployment is complete, log in to the web UI. At this point, users do not need to enter a username and password. Click on the "Amazon Sagemaker" page, enter the API URL and API token, and click on `Update Settings`.

![configure](../images/multi_user/multi-user-2.png)

### 2. After completing the page configuration and registering the administrator account, you need to manually restart the web UI to apply the API token and administrator account configuration. Once the restart is complete, go to the login page and use the administrator username and password to log in.

![admin login](../images/multi_user/multi-user-3.png)

### 3. After a successful login, navigate back to the Amazon SageMaker page, where you will see the user list.

![add user](../images/multi_user/multi-user-5.png)

### 4. To meet your specific requirements, create new users, passwords, and roles. Once you click on "Next Page," the newly created users will be visible. To ensure the configuration changes related to the new users take effect in the web UI server, it is necessary to restart the web UI again.

![add user](../images/multi_user/multi-user-8.png)


### 4. After successfully restarting the web UI, access the page and log in using the newly created username and password.

![new user login](../images/multi_user/multi-user-6.png)

### 5. When accessing the Amazon SageMaker tab, the displayed content may vary for different users.

![view new user](../images/multi_user/multi-user-7.png)
