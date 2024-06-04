# ftrack's webhook example for cascade-status-change

This recipe ports the logic of the [cascade-status-change event](https://github.com/ftrackhq/ftrack-recipes/tree/main/python/events/cascade-status-changes-0.0.0) to ftrack webhook.

## requirements

## deployment
To deploy the lambda on Amazon run:

```bash
sam deploy --guided
```

Once done, you'll find the URL of the lambda as **value** of the cloud formation output:

```
Key                 StatusChangeApi
Description         API Gateway endpoint URL for Prod stage for Status Change function
Value               https://xxxxxxxxx.execute-api.eu-north-1.amazonaws.com/Prod/status_change/
```

# parameters

* **Stack Name** (can be left as default): The name you want to give to this lambda
* **AWS Region** (can be left as default): The region where you want the lamda to deploy
* **Parameter FtrackServer** (required): the full address to your ftrack instance
* **Parameter FtrackApiKey** (required): the api key you want to use
* **Parameter FtrackApiUser** (required): the user you want to run the code
* **Confirm changes before deploy** (can be left as default): Set to **Yes**
* **Allow SAM CLI IAM role creation** (can be left as default): Set to **Yes**
* **Disable rollback**  (can be left as default): Set to **No**
* **StatusChangeFunction has no authentication. Is this okay?**  (required): Set to **Yes**

