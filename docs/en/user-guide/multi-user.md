# Configure API and Multiple Users.

## Configure API
1. After the deployment is complete, log in to the web UI. At this point, users do not need to enter a username and password. Click on the "Amazon Sagemaker" page, enter the API URL and API token, and click on `Update Settings`.
![configure](../images/multi_user/multi-user-2.png)

2. After completing the page configuration and registering the administrator account, refresh the page and log in using the administrator username and password.
![admin login](../images/multi_user/multi-user-3.png)

3. After a successful login, navigate back to the Amazon SageMaker page, where you will see the user list.
![add user](../images/multi_user/multi-user-5.png)

## Multiple User Management
### Add New User
1. To meet your specific requirements, create new users, passwords, and roles. Once you click on "Next Page," the newly created users will be visible. 
![add user](../images/multi_user/multi-user-8.png)

2. Open another incognito browser, and log in using the newly created username and password. After then, you can work as the new user.

### Manage Existing User
1. Select the corresponding user from **User Table** that is expected to be updated, including **Password** or **User Role** update. The user information will be displayed in field **Update a User Setting**.
2. Update the corresponding fields as need, and click **Upsert a User** to save the change. Otherwise click **Delete a User** to delete the selected user.


