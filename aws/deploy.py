"""Deploy the Nexus model to a SageMaker AI real-time endpoint.
Needs: pip install sagemaker; AWS credentials; an IAM role with SageMaker + S3 access.
For joblib compatibility, train locally with the same scikit-learn version as the container (framework_version 1.2-1 -> scikit-learn==1.2.2).
Usage: python aws/deploy.py --role arn:aws:iam::<acct>:role/<SageMakerRole> --bucket <your-bucket>
Then set SAGEMAKER_ENDPOINT=aquaheat-nexus in .env (delete the endpoint afterwards to stop charges)."""
import argparse, os, sys, tarfile
import joblib
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(here))
from app import model
import sagemaker
from sagemaker.sklearn import SKLearnModel

ap = argparse.ArgumentParser(); ap.add_argument("--role", required=True); ap.add_argument("--bucket", required=True)
ap.add_argument("--instance", default="ml.m5.large"); ap.add_argument("--name", default="aquaheat-nexus"); a = ap.parse_args()
joblib.dump(model, "model.joblib")
with tarfile.open("model.tar.gz", "w:gz") as t: t.add("model.joblib")
sess = sagemaker.Session(default_bucket=a.bucket)
data = sess.upload_data("model.tar.gz", bucket=a.bucket, key_prefix="aquaheat/model")
m = SKLearnModel(model_data=data, role=a.role, entry_point=os.path.join(here, "inference.py"), framework_version="1.2-1", sagemaker_session=sess)
p = m.deploy(initial_instance_count=1, instance_type=a.instance, endpoint_name=a.name)
print("Endpoint ready:", p.endpoint_name)
