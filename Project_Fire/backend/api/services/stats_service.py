from datetime import datetime, date
import logging
from api.services.firebase_service import db

logger = logging.getLogger(__name__)

class StatsService:
    @staticmethod
    async def get_dashboard_stats():
        """
        Calculate dashboard statistics efficiently.
        Returns a dictionary with detection counts.
        """
        try:
            detections_ref = db.collection('detections')
            all_docs = detections_ref.stream()
            
            stats = {
                "total_detections": 0,
                "active_fires": 0,
                "resolved_fires": 0,
                "critical_fires": 0,
                "today_detections": 0,
                "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "by_status": {"pending": 0, "verified": 0, "contained": 0, "false_alarm": 0, "resolved": 0}
            }
            
            today = date.today()
            
            for doc in all_docs:
                data = doc.to_dict()
                stats["total_detections"] += 1
                
                # Timestamp check for 'today'
                ts = data.get('timestamp')
                if ts:
                    # Firestore timestamps can be datetime objects
                    if isinstance(ts, datetime):
                        if ts.date() == today:
                            stats["today_detections"] += 1
                    elif isinstance(ts, str):
                        try:
                            if datetime.fromisoformat(ts).date() == today:
                                stats["today_detections"] += 1
                        except:
                            pass
                
                # Status & Severity
                status = data.get('status', 'pending').lower()
                severity = data.get('severity', 'low').lower()
                
                if status in stats["by_status"]:
                    stats["by_status"][status] += 1
                
                if severity in stats["by_severity"]:
                    stats["by_severity"][severity] += 1
                
                # Aggregates
                if status in ('pending', 'verified'):
                    stats["active_fires"] += 1
                elif status == 'resolved':
                    stats["resolved_fires"] += 1
                    
                if severity == 'critical':
                    stats["critical_fires"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Stats calculation error: {e}")
            raise e

stats_service = StatsService()
