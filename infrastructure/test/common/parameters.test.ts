/**
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 *  with the License. A copy of the License is located at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 *  and limitations under the License.
 */

import {App} from 'aws-cdk-lib';
import {Template} from 'aws-cdk-lib/assertions';
import {Middleware} from '../../src/main';
import {getParameter} from '../utils';

describe('common parameters test', () => {
    const app = new App();
    const testId = 'test-1';
    const stack = new Middleware(app, testId + '-sd-on-aws', {});
    const template = Template.fromStack(stack);

    beforeEach(() => {
    });

    test('Should has Parameter deployedBefore', () => {
        template.hasParameter('deployedBefore', {
            Type: 'String',
        });
    });

    test('Parameter deployedBefore must be `yes` or `no`', () => {
        const allowedValues = getParameter(template, 'deployedBefore').AllowedValues;

        const validValues = [
            'yes',
            'no',
        ];

        for (const v of validValues) {
            expect(allowedValues.includes(v)).toEqual(true);
        }

        const invalidValues = [
            '',
            'error',
        ];

        for (const v of invalidValues) {
            expect(allowedValues.includes(v)).toEqual(false);
        }
    });

    test('Should has parameter email', () => {
        template.hasParameter('email', {
            Type: 'String',
        });
    });

    test('Should has parameter ecrImageTag', () => {
        template.hasParameter('ecrImageTag', {
            Type: 'String',
        });
    });

    test('Should has parameter bucket', () => {
        template.hasParameter('bucket', {
            Type: 'String',
        });
    });

    test('Should check S3 bucket pattern', () => {

        const pattern = getParameter(template, 'bucket').AllowedPattern;
        const regex = new RegExp(`${pattern}`);

        // Bucket naming rules: https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
        const validValues = [
            'abc',
            'abc1',
            'abctest',
            'abc-test',
            'abc.test',
            'abctest-18511111111-20231019',
            'docexamplebucket1',
            'log-delivery-march-2020',
            'my-hosted-content',
            'docexamplewebsite.com',
            'www.docexamplewebsite.com',
            'my.example.s3.bucket',
        ];

        for (const v of validValues) {
            expect(v).toMatch(regex);
        }

        const invalidValues = [
            'ab',
            'ab_test',
            '',
            'ABC',
            'tooooooooooooooooooooooooooooooooooooooooloooooooooooooooooooong',
            'doc_example_bucket',
            'DocExampleBucket',
            'doc-example-bucket-',
        ];

        for (const v of invalidValues) {
            expect(v).not.toMatch(regex);
        }

    });

});
