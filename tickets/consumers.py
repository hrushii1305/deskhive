import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TicketConsumer(AsyncWebsocketConsumer):
    """
    Handles a WebSocket connection for a single ticket.
    Clients viewing the same ticket join a shared "group"; when a comment
    is added, the server broadcasts it to everyone in that ticket's group.
    """

    async def connect(self):
        self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
        self.group_name = f'ticket_{self.ticket_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        
        
    async def disconnect(self, close_code):
        # Leave the group when the client disconnects
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # This runs when the server broadcasts a "comment_message" to the group.
    # It sends the comment down the WebSocket to this connected client.
    async def comment_message(self, event):
        await self.send(text_data=json.dumps({
            'author': event['author'],
            'body': event['body'],
        }))