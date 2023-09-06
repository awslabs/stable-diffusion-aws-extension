#!/bin/bash

aws dynamodb create-table --billing-mode PAY_PER_REQUEST --cli-input-json file://user_table.json