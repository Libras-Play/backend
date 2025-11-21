#!/usr/bin/env python3
"""
Sync script for User Path Progression (FASE 2)

Syncs user path items when new topics or sign languages are added to Content Service.
Creates missing path items for existing users without modifying existing progress.

This script is IDEMPOTENT - safe to run multiple times.

Usage:
    python scripts/sync_path_with_topics.py [--batch-size 50] [--dry-run] [--language LSB]
"""
import asyncio
import argparse
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path to import app modules
sys.path.insert(0, '/app')

from app import dynamo, content_client
from app.config import get_settings
from app.schemas import VALID_SIGN_LANGUAGES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()


async def get_all_topics() -> List[Dict[str, Any]]:
    """Get all topics from Content Service"""
    try:
        topics = await content_client.get_topics()
        logger.info(f"Retrieved {len(topics)} topics from Content Service")
        return topics
    except Exception as e:
        logger.error(f"Error fetching topics: {str(e)}")
        raise


async def get_all_users(limit: int = 10000) -> List[Dict[str, Any]]:
    """Scan all users from DynamoDB"""
    try:
        logger.info(f"Scanning users from table {settings.DYNAMODB_USER_TABLE}...")
        
        users = []
        response = dynamo.db_client.user_table.scan(Limit=limit)
        users.extend(response.get('Items', []))
        
        while 'LastEvaluatedKey' in response and len(users) < limit:
            response = dynamo.db_client.user_table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                Limit=limit - len(users)
            )
            users.extend(response.get('Items', []))
        
        logger.info(f"Found {len(users)} users")
        return users
        
    except Exception as e:
        logger.error(f"Error scanning users: {str(e)}")
        raise


async def sync_user_topics(
    user_id: str,
    topics: List[Dict[str, Any]],
    learning_languages: List[str],
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Sync topics for a user across all learning languages
    
    Creates missing path items without modifying existing ones.
    
    Args:
        user_id: User identifier
        topics: List of all topics from Content Service
        learning_languages: List of sign languages to sync
        dry_run: If True, only log what would be done
        
    Returns:
        Dict with sync results
    """
    results = {
        'userId': user_id,
        'topicsCreated': 0,
        'topicsSkipped': 0,
        'languages': {}
    }
    
    for learning_language in learning_languages:
        created_for_lang = 0
        skipped_for_lang = 0
        
        for topic in topics:
            topic_id = str(topic.get('id'))
            order_index = topic.get('order_index', 0)
            
            try:
                # Check if topic has exercises for this language
                has_exercises = await content_client.topic_has_exercises_for_language(
                    topic_id,
                    learning_language
                )
                
                if not has_exercises:
                    logger.debug(
                        f"Topic {topic_id} has no exercises for {learning_language}, skipping"
                    )
                    skipped_for_lang += 1
                    continue
                
                # Check if path item already exists
                existing = await dynamo.get_path_topic(user_id, learning_language, topic_id)
                
                if existing:
                    logger.debug(
                        f"Path item already exists: user {user_id}, "
                        f"language {learning_language}, topic {topic_id}"
                    )
                    skipped_for_lang += 1
                    continue
                
                if dry_run:
                    logger.info(
                        f"[DRY RUN] Would create path item: {user_id}, "
                        f"{learning_language}, {topic_id}"
                    )
                    created_for_lang += 1
                else:
                    # Create new path item (locked by default)
                    await dynamo.create_path_item(
                        user_id=user_id,
                        topic_id=topic_id,
                        learning_language=learning_language,
                        order_index=order_index,
                        unlocked=False,  # New topics are locked
                        auto_unlocked=False,
                        manual_unlock_cost_coins=100,
                        manual_unlock_cost_gems=1
                    )
                    created_for_lang += 1
                    logger.info(
                        f"✓ Created path item: user {user_id}, "
                        f"language {learning_language}, topic {topic_id}"
                    )
                
            except Exception as e:
                logger.error(
                    f"Error syncing topic {topic_id} for user {user_id}, "
                    f"language {learning_language}: {str(e)}"
                )
        
        results['languages'][learning_language] = {
            'created': created_for_lang,
            'skipped': skipped_for_lang
        }
        results['topicsCreated'] += created_for_lang
        results['topicsSkipped'] += skipped_for_lang
    
    return results


async def main(
    batch_size: int = 50,
    dry_run: bool = False,
    language_filter: Optional[str] = None,
    limit: int = None
):
    """
    Main sync process
    
    Args:
        batch_size: Number of users to process in parallel
        dry_run: If True, only log what would be done
        language_filter: Only sync for specific language (e.g., 'LSB')
        limit: Maximum number of users to process (for testing)
    """
    start_time = datetime.utcnow()
    logger.info("=" * 80)
    logger.info("SYNC PATH WITH TOPICS - FASE 2")
    logger.info("=" * 80)
    logger.info(f"Started at: {start_time.isoformat()}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Language filter: {language_filter or 'All languages'}")
    logger.info(f"Limit: {limit or 'No limit'}")
    logger.info("=" * 80)
    
    try:
        # Get all topics
        topics = await get_all_topics()
        if not topics:
            logger.warning("No topics found in Content Service. Exiting.")
            return
        
        # Determine languages to sync
        languages_to_sync = [language_filter] if language_filter else VALID_SIGN_LANGUAGES
        
        logger.info(f"Languages to sync: {', '.join(languages_to_sync)}")
        logger.info(f"Total topics to sync: {len(topics)}")
        
        # Get all users
        users = await get_all_users(limit=limit or 10000)
        total_users = len(users)
        
        if total_users == 0:
            logger.warning("No users found. Exiting.")
            return
        
        logger.info(f"Processing {total_users} users in batches of {batch_size}...")
        
        # Process users in batches
        all_results = []
        processed = 0
        total_created = 0
        total_skipped = 0
        
        for i in range(0, total_users, batch_size):
            batch = users[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_users + batch_size - 1) // batch_size
            
            logger.info(f"\n--- Batch {batch_num}/{total_batches} ---")
            
            # Process batch in parallel
            tasks = [
                sync_user_topics(
                    user_id=user.get('user_id'),
                    topics=topics,
                    learning_languages=languages_to_sync,
                    dry_run=dry_run
                )
                for user in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch task failed: {str(result)}")
                else:
                    all_results.append(result)
                    processed += 1
                    total_created += result.get('topicsCreated', 0)
                    total_skipped += result.get('topicsSkipped', 0)
            
            logger.info(
                f"Batch {batch_num} complete: {len(batch)} users processed, "
                f"{sum(r.get('topicsCreated', 0) for r in batch_results if not isinstance(r, Exception))} items created"
            )
            
            # Small delay between batches
            if i + batch_size < total_users:
                await asyncio.sleep(0.5)
        
        # Summary
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("SYNC COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total users processed: {processed}/{total_users}")
        logger.info(f"Total path items created: {total_created}")
        logger.info(f"Total items skipped (already exist): {total_skipped}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Average: {duration/total_users:.2f} seconds per user")
        logger.info("=" * 80)
        
        # Save results to file
        if not dry_run:
            results_file = f'sync_results_{start_time.strftime("%Y%m%d_%H%M%S")}.json'
            import json
            with open(results_file, 'w') as f:
                json.dump({
                    'startTime': start_time.isoformat(),
                    'endTime': end_time.isoformat(),
                    'duration': duration,
                    'totalUsers': total_users,
                    'processed': processed,
                    'totalCreated': total_created,
                    'totalSkipped': total_skipped,
                    'topicsCount': len(topics),
                    'languagesProcessed': languages_to_sync,
                    'results': all_results
                }, f, indent=2)
            logger.info(f"Results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"Fatal error in sync: {str(e)}", exc_info=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sync Path with Topics from Content Service')
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of users to process in parallel (default: 50)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no DB writes)'
    )
    parser.add_argument(
        '--language',
        type=str,
        choices=VALID_SIGN_LANGUAGES,
        default=None,
        help='Only sync for specific sign language (LSB, ASL, or LSM)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of users to process (for testing)'
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        language_filter=args.language,
        limit=args.limit
    ))
