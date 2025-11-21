#!/usr/bin/env python3
"""
Backfill script for User Path Progression (FASE 2)

Migrates existing users to the new UserPathProgress table.
For each user, creates path items for all topics across all sign languages.

This script is IDEMPOTENT - safe to run multiple times.

Usage:
    python scripts/backfill_user_path.py [--batch-size 50] [--dry-run]
"""
import asyncio
import argparse
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path to import app modules
sys.path.insert(0, '/app')

from app import dynamo, content_client
from app.logic import path_logic
from app.config import get_settings
from app.schemas import VALID_SIGN_LANGUAGES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()


async def get_all_users(limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Scan all users from DynamoDB user-data table
    
    Args:
        limit: Maximum number of users to process (for testing)
        
    Returns:
        List of user data dicts
    """
    try:
        logger.info(f"Scanning users from table {settings.DYNAMODB_USER_TABLE}...")
        
        users = []
        response = dynamo.db_client.user_table.scan(Limit=limit)
        
        users.extend(response.get('Items', []))
        
        # Handle pagination if needed
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


async def backfill_user(
    user_id: str,
    learning_languages: List[str],
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Backfill path progression for a single user across all learning languages
    
    Args:
        user_id: User identifier
        learning_languages: List of sign languages to initialize (e.g., ['LSB', 'ASL', 'LSM'])
        dry_run: If True, only log what would be done without writing to DB
        
    Returns:
        Dict with results for each language
    """
    results = {
        'userId': user_id,
        'languages': {},
        'totalTopicsCreated': 0,
        'errors': []
    }
    
    for learning_language in learning_languages:
        try:
            logger.info(f"Backfilling user {user_id} for language {learning_language}...")
            
            if dry_run:
                logger.info(f"[DRY RUN] Would initialize path for {user_id}, {learning_language}")
                results['languages'][learning_language] = {
                    'topicsCreated': 0,
                    'firstTopicUnlocked': False,
                    'dryRun': True
                }
            else:
                # Initialize path for this language
                init_result = await path_logic.initialize_user_path(user_id, learning_language)
                
                results['languages'][learning_language] = init_result
                results['totalTopicsCreated'] += init_result.get('topicsCreated', 0)
                
                logger.info(
                    f"✓ User {user_id}, language {learning_language}: "
                    f"{init_result.get('topicsCreated', 0)} topics created"
                )
            
        except Exception as e:
            error_msg = f"Error backfilling {user_id} for {learning_language}: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
    
    return results


async def main(batch_size: int = 50, dry_run: bool = False, limit: int = None):
    """
    Main backfill process
    
    Args:
        batch_size: Number of users to process in parallel
        dry_run: If True, only log what would be done
        limit: Maximum number of users to process (for testing)
    """
    start_time = datetime.utcnow()
    logger.info("=" * 80)
    logger.info("BACKFILL USER PATH PROGRESSION - FASE 2")
    logger.info("=" * 80)
    logger.info(f"Started at: {start_time.isoformat()}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Limit: {limit or 'No limit'}")
    logger.info(f"Sign languages: {', '.join(VALID_SIGN_LANGUAGES)}")
    logger.info("=" * 80)
    
    try:
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
        errors = 0
        total_topics_created = 0
        
        for i in range(0, total_users, batch_size):
            batch = users[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_users + batch_size - 1) // batch_size
            
            logger.info(f"\n--- Batch {batch_num}/{total_batches} ---")
            
            # Process batch in parallel
            tasks = [
                backfill_user(
                    user_id=user.get('user_id'),
                    learning_languages=VALID_SIGN_LANGUAGES,
                    dry_run=dry_run
                )
                for user in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch task failed: {str(result)}")
                    errors += 1
                else:
                    all_results.append(result)
                    processed += 1
                    total_topics_created += result.get('totalTopicsCreated', 0)
                    
                    if result.get('errors'):
                        errors += len(result['errors'])
            
            logger.info(
                f"Batch {batch_num} complete: {len(batch)} users processed, "
                f"{sum(r.get('totalTopicsCreated', 0) for r in batch_results if not isinstance(r, Exception))} topics created"
            )
            
            # Small delay between batches to avoid throttling
            if i + batch_size < total_users:
                await asyncio.sleep(0.5)
        
        # Summary
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total users processed: {processed}/{total_users}")
        logger.info(f"Total topics created: {total_topics_created}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Average: {duration/total_users:.2f} seconds per user")
        logger.info("=" * 80)
        
        # Save results to file
        if not dry_run:
            results_file = f'backfill_results_{start_time.strftime("%Y%m%d_%H%M%S")}.json'
            import json
            with open(results_file, 'w') as f:
                json.dump({
                    'startTime': start_time.isoformat(),
                    'endTime': end_time.isoformat(),
                    'duration': duration,
                    'totalUsers': total_users,
                    'processed': processed,
                    'totalTopicsCreated': total_topics_created,
                    'errors': errors,
                    'results': all_results
                }, f, indent=2)
            logger.info(f"Results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"Fatal error in backfill: {str(e)}", exc_info=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill User Path Progression')
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
        '--limit',
        type=int,
        default=None,
        help='Maximum number of users to process (for testing)'
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        limit=args.limit
    ))
