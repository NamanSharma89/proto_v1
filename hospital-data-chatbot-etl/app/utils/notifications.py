import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from app.config.settings import ETLConfig
from app.utils.logging import get_logger

logger = get_logger(__name__)

class NotificationManager:
    """Handles notifications for ETL processes."""
    
    def __init__(self):
        self.config = ETLConfig()
        self.notification_config = self.config.get_notification_config()
        
        # Initialize AWS SNS client if needed
        if (self.notification_config.get('enabled') and 
            'sns' in self.notification_config):
            try:
                self.sns_client = boto3.client(
                    'sns', 
                    region_name=self.config.AWS_REGION
                )
            except Exception as e:
                logger.warning(f"Failed to initialize SNS client: {str(e)}")
                self.sns_client = None
        else:
            self.sns_client = None

    def send_etl_completion_notification(self, etl_stats: Dict[str, Any]):
        """Send notification when ETL process completes."""
        if not self.notification_config.get('enabled'):
            logger.debug("Notifications disabled, skipping")
            return
        
        # Prepare notification content
        notification_data = self._prepare_notification_data(etl_stats)
        
        # Send to configured channels
        results = {}
        
        if 'sns' in self.notification_config:
            results['sns'] = self._send_sns_notification(notification_data)
        
        if 'slack' in self.notification_config:
            results['slack'] = self._send_slack_notification(notification_data)
        
        logger.info(f"Notification results: {results}")
        return results

    def _prepare_notification_data(self, etl_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare notification data from ETL statistics."""
        status = etl_stats.get('status', 'unknown')
        
        # Determine notification level
        if status in ['completed_success', 'completed_no_files']:
            level = 'success'
            emoji = '✅'
        elif status == 'completed_partial':
            level = 'warning'
            emoji = '⚠️'
        else:
            level = 'error'
            emoji = '❌'
        
        # Build notification content
        notification = {
            'level': level,
            'emoji': emoji,
            'title': f"Hospital Data ETL {status.replace('_', ' ').title()}",
            'run_id': etl_stats.get('run_id', 'unknown'),
            'environment': self.config.get_environment_name(),
            'status': status,
            'duration': f"{etl_stats.get('duration_seconds', 0):.1f}s",
            'files_processed': etl_stats.get('files_processed', 0),
            'files_failed': etl_stats.get('files_failed', 0),
            'records_processed': etl_stats.get('records_processed', 0),
            'timestamp': datetime.now().isoformat(),
            'errors': etl_stats.get('errors', []),
            'warnings': etl_stats.get('warnings', [])
        }
        
        return notification

    def _send_sns_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification via AWS SNS."""
        if not self.sns_client:
            return {'success': False, 'error': 'SNS client not initialized'}
        
        try:
            topic_arn = self.notification_config['sns']['topic_arn']
            
            # Prepare message
            subject = f"[{notification_data['environment']}] {notification_data['title']}"
            
            message_parts = [
                f"ETL Run: {notification_data['run_id']}",
                f"Status: {notification_data['emoji']} {notification_data['status']}",
                f"Environment: {notification_data['environment']}",
                f"Duration: {notification_data['duration']}",
                f"Files Processed: {notification_data['files_processed']}",
                f"Files Failed: {notification_data['files_failed']}",
                f"Records Processed: {notification_data['records_processed']:,}",
                f"Timestamp: {notification_data['timestamp']}"
            ]
            
            if notification_data['errors']:
                message_parts.append(f"\nErrors ({len(notification_data['errors'])}):")
                for error in notification_data['errors'][:3]:  # Limit to first 3
                    message_parts.append(f"- {error.get('message', 'Unknown error')}")
                if len(notification_data['errors']) > 3:
                    message_parts.append(f"... and {len(notification_data['errors']) - 3} more")
            
            if notification_data['warnings']:
                message_parts.append(f"\nWarnings ({len(notification_data['warnings'])}):")
                for warning in notification_data['warnings'][:3]:  # Limit to first 3
                    message_parts.append(f"- {warning}")
                if len(notification_data['warnings']) > 3:
                    message_parts.append(f"... and {len(notification_data['warnings']) - 3} more")
            
            message = '\n'.join(message_parts)
            
            # Send SNS message
            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=subject,
                Message=message
            )
            
            logger.info(f"SNS notification sent successfully: {response['MessageId']}")
            return {'success': True, 'message_id': response['MessageId']}
            
        except ClientError as e:
            logger.error(f"Failed to send SNS notification: {str(e)}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error sending SNS notification: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _send_slack_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification via Slack webhook."""
        try:
            webhook_url = self.notification_config['slack']['webhook_url']
            
            # Determine color based on level
            color_map = {
                'success': 'good',
                'warning': 'warning', 
                'error': 'danger'
            }
            color = color_map.get(notification_data['level'], 'warning')
            
            # Build Slack message
            slack_message = {
                "username": "Hospital ETL Bot",
                "icon_emoji": ":hospital:",
                "attachments": [
                    {
                        "color": color,
                        "title": notification_data['title'],
                        "fields": [
                            {
                                "title": "Run ID",
                                "value": notification_data['run_id'],
                                "short": True
                            },
                            {
                                "title": "Environment",
                                "value": notification_data['environment'],
                                "short": True
                            },
                            {
                                "title": "Duration",
                                "value": notification_data['duration'],
                                "short": True
                            },
                            {
                                "title": "Status",
                                "value": f"{notification_data['emoji']} {notification_data['status']}",
                                "short": True
                            },
                            {
                                "title": "Files Processed",
                                "value": str(notification_data['files_processed']),
                                "short": True
                            },
                            {
                                "title": "Records Processed",
                                "value": f"{notification_data['records_processed']:,}",
                                "short": True
                            }
                        ],
                        "footer": "Hospital Data ETL",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # Add error information if present
            if notification_data['files_failed'] > 0:
                slack_message["attachments"][0]["fields"].append({
                    "title": "Files Failed",
                    "value": str(notification_data['files_failed']),
                    "short": True
                })
            
            if notification_data['errors']:
                error_text = "\n".join([
                    f"• {error.get('message', 'Unknown error')}" 
                    for error in notification_data['errors'][:5]
                ])
                if len(notification_data['errors']) > 5:
                    error_text += f"\n... and {len(notification_data['errors']) - 5} more errors"
                
                slack_message["attachments"][0]["fields"].append({
                    "title": "Errors",
                    "value": error_text,
                    "short": False
                })
            
            # Send Slack message
            response = requests.post(
                webhook_url,
                json=slack_message,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
                return {'success': True}
            else:
                logger.error(f"Slack notification failed: {response.status_code} - {response.text}")
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_test_notification(self) -> Dict[str, Any]:
        """Send a test notification to verify configuration."""
        if not self.notification_config.get('enabled'):
            return {'success': False, 'error': 'Notifications are disabled'}
        
        # Create test notification data
        test_stats = {
            'run_id': f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'status': 'completed_success',
            'duration_seconds': 45.2,
            'files_processed': 1,
            'files_failed': 0,
            'records_processed': 1500,
            'records_failed': 0,
            'errors': [],
            'warnings': ['This is a test notification']
        }
        
        logger.info("Sending test notification...")
        return self.send_etl_completion_notification(test_stats)