#!/usr/bin/python2.7

import boto3
import os
from datetime import datetime, timedelta

account = os.environ['account']
sns = os.environ['sns_topic']

# Main function Lambda will run at start
def lambda_handler(event, context):
    snapshot_deleted = redshift_snapshot_remover()
    snapshot_success = redshift_manual_snap()
    if snapshot_deleted and snapshot_success:
        return "Completed"
    else:
        return "Failure"

# Function to connect to AWS services
def connect(service):
    print 'Connecting to AWS Service: ' + service
    client = boto3.client(service)
    if client is None:
        msg = 'Connection to ' + service + 'failed in'
        notify_devops('Redshift manual snapshot Lambda function: FAILURE in account: ' + account, msg)
    return client

# Function to take manual snapshot of the latest automated snapshot for each Redshift Cluster
def redshift_manual_snap():
    print 'Running function for Redshift manual snapshot copy'
    try:
        client = connect('redshift')
        snapshots = client.describe_cluster_snapshots(
            SnapshotType='automated')
        snap = snapshots["Snapshots"]
        
        # Sorting the snap dict (Most recent date first)
        sort_snap = sorted(snap, key=lambda x: x['SnapshotCreateTime'], reverse=True)
        
        '''
        Looping through the sorted dict and appending "Cluster Indentifier" if not existing in "copied" array
         - creating cluster snapshot for each of the ClusterIdentifier added
         '''
        copied = []
        man_snaps = []
        
        for s in sort_snap:
            if not s['ClusterIdentifier'] in copied:
                print 'Found new cluster: ' + s['ClusterIdentifier'] + '. Adding to list.'
                copied.append(s['ClusterIdentifier'])
                print 'Taking manual snapshot from automated Snapshot ID: ' + s['SnapshotIdentifier']
                client.create_cluster_snapshot(
                    SnapshotIdentifier = s['SnapshotIdentifier'][3:],
                    ClusterIdentifier = s['ClusterIdentifier'])
                print 'Adding manual snapshot to the list'
                man_snaps.append(s['SnapshotIdentifier'][3:])
                print 'Current snapshot list: ' + ', '.join(man_snaps)
        final_snaps = ', '.join(man_snaps)
        print 'The following manual snapshots were taken: ' + final_snaps
        return True
    except Exception as e:
        print str(e)
        notify_devops('Redshift manual snapshot Lambda function: FAILURE in account: ' + account, str(e) + '. Please check Cloudwatch Logs')
        return False

# Function to remove manual snapshots which are older than specified in retention period variable
def redshift_snapshot_remover():
    print 'Running function to remove old snapshots'
    try:
        client = connect('redshift')
        snapshots = client.describe_cluster_snapshots(SnapshotType='manual')
        snap = snapshots["Snapshots"]
        # Number of days to keep manual snapshots
        ret_period = os.environ['ret_period']
        # Maximum days to look back for manual snapshots to avoid deleting old snapshots still needed
        max_back = os.environ['max_back']
        del_snapshot = []
        
        removal_date = (datetime.now() - timedelta(days=int(ret_period))).date()
        max_look_back = (datetime.now() - timedelta(days=int(max_back))).date()
        # Looping through snap and removing snapshots which are older than retention period
        for s in snap:
            snap_date = s['SnapshotCreateTime'].date()
            # Condition for date older than retention period and condition to keep manual snapshots created by other person in the past
            if ((snap_date < removal_date) and (snap_date > max_look_back)):
                print 'Found snapshot older than retention period: ' + s['SnapshotIdentifier'] + '. Adding to the list.'
                del_snapshot.append(s['SnapshotIdentifier'])
                print 'Removing old snapshot: ' + s['SnapshotIdentifier']
                client.delete_cluster_snapshot(
                    SnapshotIdentifier=s['SnapshotIdentifier'],
                    SnapshotClusterIdentifier=s['ClusterIdentifier']
                )
        deleted_snapshots = ', '.join(del_snapshot)
        if not deleted_snapshots:
            print 'No snapshots were found to be deleted'
        else:
            print 'List of deleted snapshots: ' + deleted_snapshots
        return True
    except Exception as e:
        print str(e)
        notify_devops('Redshift manual snapshot Lambda function: FAILURE in account: ' + account, str(e) + '. Please check Cloudwatch Logs')
        return False

# Function to notify DevOps team in case of a snapshot failure
def notify_devops(sub, msg):
    print 'Notifying DevOps team'
    client = connect('sns')
    pub_msg = client.publish(
        TopicArn = sns,
        Message = msg,
        Subject = sub
        )
    return pub_msg