"""
Push notification service for mobile and web notifications.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from logger import logger


class PushNotificationService:
    """Service for sending push notifications."""
    
    def __init__(self):
        self.fcm_enabled = False  # Firebase Cloud Messaging
        self.web_push_enabled = False  # Web Push API
        
        # In production, these would be loaded from environment variables
        self.fcm_config = {
            "server_key": "",
            "sender_id": ""
        }
        
        self.web_push_config = {
            "vapid_public_key": "",
            "vapid_private_key": "",
            "vapid_email": ""
        }
        
        # Mock device storage for development
        self.mock_devices = {}
    
    async def register_device(self, user_id: str, device_token: str, device_type: str) -> Dict[str, Any]:
        """Register device for push notifications."""
        try:
            # In production, this would store in database
            if user_id not in self.mock_devices:
                self.mock_devices[user_id] = []
            
            device_info = {
                "token": device_token,
                "type": device_type,
                "registered_at": datetime.utcnow().isoformat(),
                "active": True
            }
            
            # Remove existing device if updating
            self.mock_devices[user_id] = [
                d for d in self.mock_devices[user_id] if d["token"] != device_token
            ]
            
            self.mock_devices[user_id].append(device_info)
            
            logger.info(f"Registered device for user {user_id}: {device_type}")
            
            return {
                "success": True,
                "device_id": device_token[:10] + "...",
                "message": "Device registered successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            return {"success": False, "error": str(e)}
    
    async def unregister_device(self, user_id: str, device_token: str) -> Dict[str, Any]:
        """Unregister device from push notifications."""
        try:
            if user_id in self.mock_devices:
                original_count = len(self.mock_devices[user_id])
                self.mock_devices[user_id] = [
                    d for d in self.mock_devices[user_id] if d["token"] != device_token
                ]
                
                removed_count = original_count - len(self.mock_devices[user_id])
                
                if removed_count > 0:
                    logger.info(f"Unregistered device for user {user_id}")
                    return {"success": True, "message": "Device unregistered"}
                else:
                    return {"success": False, "error": "Device not found"}
            
            return {"success": False, "error": "User has no registered devices"}
            
        except Exception as e:
            logger.error(f"Failed to unregister device: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_push_notification(self, user_id: str, title: str, body: str, 
                                   action_url: str = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send push notification to user's devices."""
        try:
            # Get user devices
            user_devices = self.mock_devices.get(user_id, [])
            active_devices = [d for d in user_devices if d.get("active", True)]
            
            if not active_devices:
                return {
                    "success": False,
                    "error": "No active devices found for user",
                    "devices_attempted": 0
                }
            
            results = {
                "success": True,
                "devices_attempted": len(active_devices),
                "devices_successful": 0,
                "devices_failed": 0,
                "failures": []
            }
            
            # Send to each device
            for device in active_devices:
                try:
                    device_result = await self._send_to_device(
                        device, title, body, action_url, data
                    )
                    
                    if device_result["success"]:
                        results["devices_successful"] += 1
                    else:
                        results["devices_failed"] += 1
                        results["failures"].append({
                            "device_type": device["type"],
                            "error": device_result.get("error", "Unknown error")
                        })
                        
                except Exception as e:
                    results["devices_failed"] += 1
                    results["failures"].append({
                        "device_type": device.get("type", "unknown"),
                        "error": str(e)
                    })
            
            # Log notification
            logger.info(
                f"Push notification sent to user {user_id}: "
                f"{results['devices_successful']}/{results['devices_attempted']} devices successful"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_bulk_push_notification(self, user_ids: List[str], title: str, body: str,
                                        action_url: str = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send push notification to multiple users."""
        try:
            results = {
                "total_users": len(user_ids),
                "successful_users": 0,
                "failed_users": 0,
                "total_devices": 0,
                "successful_devices": 0,
                "failed_devices": 0,
                "errors": []
            }
            
            # Send to each user
            for user_id in user_ids:
                try:
                    user_result = await self.send_push_notification(
                        user_id, title, body, action_url, data
                    )
                    
                    if user_result.get("success"):
                        results["successful_users"] += 1
                        results["total_devices"] += user_result.get("devices_attempted", 0)
                        results["successful_devices"] += user_result.get("devices_successful", 0)
                        results["failed_devices"] += user_result.get("devices_failed", 0)
                    else:
                        results["failed_users"] += 1
                        results["errors"].append(f"User {user_id}: {user_result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    results["failed_users"] += 1
                    results["errors"].append(f"User {user_id}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to send bulk push notification: {e}")
            return {"error": str(e)}
    
    async def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """Get registered devices for user."""
        try:
            devices = self.mock_devices.get(user_id, [])
            
            # Return sanitized device info
            return [
                {
                    "device_id": device["token"][:10] + "...",
                    "type": device["type"],
                    "registered_at": device["registered_at"],
                    "active": device.get("active", True)
                }
                for device in devices
            ]
            
        except Exception as e:
            logger.error(f"Failed to get user devices: {e}")
            return []
    
    async def update_device_status(self, user_id: str, device_token: str, active: bool) -> bool:
        """Update device active status."""
        try:
            if user_id in self.mock_devices:
                for device in self.mock_devices[user_id]:
                    if device["token"] == device_token:
                        device["active"] = active
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update device status: {e}")
            return False
    
    async def _send_to_device(self, device: Dict[str, Any], title: str, body: str,
                            action_url: str = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send notification to specific device."""
        try:
            device_type = device.get("type", "unknown")
            device_token = device.get("token", "")
            
            if device_type == "android" or device_type == "ios":
                return await self._send_fcm_notification(device_token, title, body, action_url, data)
            elif device_type == "web":
                return await self._send_web_push_notification(device_token, title, body, action_url, data)
            else:
                return {"success": False, "error": f"Unsupported device type: {device_type}"}
                
        except Exception as e:
            logger.error(f"Failed to send to device: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_fcm_notification(self, device_token: str, title: str, body: str,
                                   action_url: str = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send Firebase Cloud Messaging notification."""
        try:
            if not self.fcm_enabled:
                # Mock FCM for development
                logger.info(f"[MOCK FCM] Sent notification: {title} - {body}")
                return {"success": True, "message": "Mock FCM notification sent"}
            
            # In production, would use FCM SDK
            # payload = {
            #     "to": device_token,
            #     "notification": {
            #         "title": title,
            #         "body": body
            #     },
            #     "data": data or {}
            # }
            # 
            # if action_url:
            #     payload["notification"]["click_action"] = action_url
            # 
            # response = await self._send_fcm_request(payload)
            # return response
            
            return {"success": True, "message": "FCM not configured"}
            
        except Exception as e:
            logger.error(f"Failed to send FCM notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_web_push_notification(self, subscription: str, title: str, body: str,
                                        action_url: str = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send Web Push notification."""
        try:
            if not self.web_push_enabled:
                # Mock Web Push for development
                logger.info(f"[MOCK WEB PUSH] Sent notification: {title} - {body}")
                return {"success": True, "message": "Mock Web Push notification sent"}
            
            # In production, would use pywebpush
            # from pywebpush import webpush, WebPushException
            # 
            # payload = json.dumps({
            #     "title": title,
            #     "body": body,
            #     "url": action_url,
            #     "data": data or {}
            # })
            # 
            # response = webpush(
            #     subscription_info=json.loads(subscription),
            #     data=payload,
            #     vapid_private_key=self.web_push_config["vapid_private_key"],
            #     vapid_claims={
            #         "sub": f"mailto:{self.web_push_config['vapid_email']}"
            #     }
            # )
            # 
            # return {"success": True, "response": response}
            
            return {"success": True, "message": "Web Push not configured"}
            
        except Exception as e:
            logger.error(f"Failed to send Web Push notification: {e}")
            return {"success": False, "error": str(e)}
    
    def enable_fcm(self, server_key: str, sender_id: str):
        """Enable Firebase Cloud Messaging."""
        self.fcm_config["server_key"] = server_key
        self.fcm_config["sender_id"] = sender_id
        self.fcm_enabled = True
        logger.info("FCM enabled")
    
    def enable_web_push(self, vapid_public_key: str, vapid_private_key: str, vapid_email: str):
        """Enable Web Push notifications."""
        self.web_push_config["vapid_public_key"] = vapid_public_key
        self.web_push_config["vapid_private_key"] = vapid_private_key
        self.web_push_config["vapid_email"] = vapid_email
        self.web_push_enabled = True
        logger.info("Web Push enabled")
    
    def get_web_push_public_key(self) -> str:
        """Get VAPID public key for web push subscription."""
        return self.web_push_config["vapid_public_key"]
    
    async def cleanup_inactive_devices(self, days: int = 30) -> Dict[str, Any]:
        """Clean up inactive devices."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            total_removed = 0
            
            for user_id in list(self.mock_devices.keys()):
                original_count = len(self.mock_devices[user_id])
                
                # Remove devices that haven't been active
                self.mock_devices[user_id] = [
                    device for device in self.mock_devices[user_id]
                    if device.get("active", True) and 
                       datetime.fromisoformat(device["registered_at"]) > cutoff_date
                ]
                
                removed_count = original_count - len(self.mock_devices[user_id])
                total_removed += removed_count
                
                # Remove empty user entries
                if not self.mock_devices[user_id]:
                    del self.mock_devices[user_id]
            
            logger.info(f"Cleaned up {total_removed} inactive devices")
            
            return {
                "devices_removed": total_removed,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup inactive devices: {e}")
            return {"error": str(e)}


# Global instance
push_service = PushNotificationService()