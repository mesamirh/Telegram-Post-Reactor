import os
import json
import asyncio
import random
from pyrogram import Client, filters

class TelegramAccountManager:
    def __init__(self, config_path: str = 'config.json'):
        self.config = self._load_config(config_path)
        self.clients = []
        self.channel = self.config['channel']
        self.reactions = self.config['reactions']
        self.api_id = self.config['api_id']
        self.api_hash = self.config['api_hash']
        self.channel_id = None
        self.processed_messages = set()
        self.max_retries = 3
        self.retry_delay = 5

    def _load_config(self, config_path: str):
        with open(config_path, 'r') as f:
            return json.load(f)

    async def get_channel_id(self, client):
        try:
            if isinstance(self.channel, str) and self.channel.startswith('@'):
                chat = await client.get_chat(self.channel)
                return chat.id
            return int(self.channel)
        except Exception as e:
            print(f"❌ Error resolving channel: {str(e)}")
            return None

    async def initialize_clients(self):
        os.makedirs('sessions', exist_ok=True)

        if os.path.exists('sessions'):
            for session_file in os.listdir('sessions'):
                if session_file.endswith('.session'):
                    session_name = session_file[:-8]
                    client = Client(
                        f"sessions/{session_name}",
                        api_id=self.api_id,
                        api_hash=self.api_hash
                    )
                    await client.start()
                    self.clients.append(client)
                    print(f"✅ Loaded account: {session_name}")

                    if self.channel_id is None:
                        self.channel_id = await self.get_channel_id(client)
                        if self.channel_id is None:
                            print("❌ Failed to resolve channel. Please check channel username/ID")
                            return False

        while True:
            try:
                if not self.clients:
                    print("\n❗ No accounts found. Adding first account...")
                    add_account = 'y'
                else:
                    add_account = input("\nAdd another account? (y/n): ").lower()
                
                if add_account != 'y':
                    break
                
                next_num = len(self.clients) + 1
                client = Client(
                    f"sessions/account_{next_num}",
                    api_id=self.api_id,
                    api_hash=self.api_hash
                )
                await client.start()
                self.clients.append(client)
                print(f"✅ Added new account #{next_num}")

                if self.channel_id is None:
                    self.channel_id = await self.get_channel_id(client)
                    if self.channel_id is None:
                        return False

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Failed to add account: {str(e)}")
                break

        print(f"\n✨ Total accounts active: {len(self.clients)}")
        return True

    async def react_to_message(self, message_id):
        if message_id in self.processed_messages:
            return
        
        self.processed_messages.add(message_id)
        for client in self.clients:
            retries = 0
            while retries < self.max_retries:
                try:
                    num_reactions = random.randint(1, 2)
                    selected_reactions = random.sample(self.reactions, num_reactions)
                    
                    for reaction in selected_reactions:
                        await client.send_reaction(
                            chat_id=self.channel_id,
                            message_id=message_id,
                            emoji=reaction
                        )
                        await asyncio.sleep(random.uniform(2, 4))
                    
                    break
                
                except Exception as e:
                    retries += 1
                    if retries < self.max_retries:
                        print(f"⚠️ Retry {retries}/{self.max_retries} for message {message_id}")
                        await asyncio.sleep(self.retry_delay * retries)
                    else:
                        print(f"❌ Failed to react to message {message_id} after {self.max_retries} retries")

            await asyncio.sleep(random.uniform(4, 7))

    async def process_old_messages(self):
        print("\n📜 Processing existing messages...")
        try:
            client = self.clients[0]
            async for message in client.get_chat_history(self.channel_id, limit=100):
                await self.react_to_message(message.id)
                await asyncio.sleep(random.uniform(5, 8))
        except Exception as e:
            print(f"❌ Error processing old messages: {str(e)}")
        print("✅ Finished processing existing messages")

    async def handle_new_message(self, client, message):
        await asyncio.sleep(random.uniform(1, 3))
        await self.react_to_message(message.id)

    async def run(self):
        try:
            if not await self.initialize_clients():
                return

            if not self.clients:
                print("❌ No accounts initialized. Exiting...")
                return

            await self.process_old_messages()

            for client in self.clients:
                @client.on_message(filters.channel & filters.chat(self.channel_id))
                async def message_handler(client, message):
                    await self.handle_new_message(client, message)

            print(f"\n🚀 Bot is running! Monitoring channel: {self.channel}")
            print("Press Ctrl+C to stop")
            
            await asyncio.Event().wait()

        except KeyboardInterrupt:
            print("\n👋 Stopping bot...")
        finally:
            for client in self.clients:
                await client.stop()

async def main():
    manager = TelegramAccountManager()
    await manager.run()

if __name__ == "__main__":
    asyncio.run(main())
