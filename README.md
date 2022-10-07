<!---
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights #Reserved.

This library is licensed under the MIT-0 License. See the LICENSE file.

or in the "license" file accompanying this file. This file is distributed on an "AS IS"
BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under the License.
--->

# neptune-fraud-detection-with-opensearch

Terraform module to create a Neptune database cluster.

## Architecture

![Architecture Diagram](documents/architecture_diagram.png)

## Deploying the solution

1. Create a local directory called NeptuneOpenSearchDemo and clone the source code repository:

```bash
mkdir -p $HOME/NeptuneOpenSearchDemo/
cd $HOME/NeptuneOpenSearchDemo/
git clone https://github.com/aws-samples/neptune-fraud-detection-with-opensearch.git
```

2. Change directory into the terraform directory:

```bash
cd $HOME/NeptuneOpenSearchDemo/neptune-fraud-detection-with-opensearch/terraform
```

3. Make sure the Docker daemon is running:

```bash
docker info
```

If the previous command outputs an error that is unable to connect to the Docker daemon, start Docker and run the command again.

4. Preview the changes you are about to deploy:

```bash
terraform plan
```

5. Deploy the AWS services:

```bash
terraform apply
```

> Note: Deployment will take around 30 minutes due to the creation of Neptune and OpenSearch clusters.

## Testing the solution

1. Retrieve the name of the S3 bucket to upload data to:

```bash
aws s3 ls | grep neptunestream-loader
```

The output should look like `neptunestream-loader-us-east-1-123456789012`. Confirm the bucket is in the region and account where the solution was deployed.

2. Upload node data to the S3 bucket obtained in the previous step:

```bash
aws s3 cp $HOME/NeptuneOpenSearchDemo/neptune-fraud-detection-with-opensearch/data s3://neptunestream-loader-us-east-1-123456789012 --recursive
```

3. Confirm the lambda function that sends a request to OpenSearch was deployed correctly:

```bash
aws lambda get-function --function-name NeptuneStreamOpenSearchRequestLambda
```

4. Invoke the lambda function to see all records present in OpenSearch that are added from Neptune:

```bash
aws lambda invoke --function-name NeptuneStreamOpenSearchRequestLambda response.json
```

## Cleanup

1. Clean up the resources deployed in the solution:

```bash
terraform destroy --auto-approve
```
