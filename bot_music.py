import asyncio
from collections import deque
import re
import discord
from discord.ext import commands
import youtube_dl

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
bot = commands.Bot(command_prefix='*', intents=intents)

class Song:
    def __init__(self, url, title):
        self.url = url
        self.title = title

# Sự kiện khi bot hoạt động
@bot.event
async def on_ready():
    print(f'Bot đã sẵn sàng. Tên: {bot.user.name}. ID: {bot.user.id}')

is_playing = False
queue = []
save_queue = []
repeat_mode = False
repeat_queue = False

@bot.command(name="play", aliases=["p","playing"], help="Phát nhạc")
async def play(ctx, *, query):
    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()
    else:
        await ctx.voice_client.move_to(voice_channel)

    if "playlist?list=" in query:
        await add_playlist_to_queue(ctx, query)
    else:
        await add_song_to_queue(ctx, query)

    if not is_playing:
        await play_song(ctx)

async def add_song_to_queue(ctx, url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info['title']
        url2 = info['formats'][0]['url']

    song = Song(url, title)
    queue.append(song)
    await ctx.send(f'Đã thêm {title} vào danh sách phát nhạc!')

async def add_playlist_to_queue(ctx, url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'extract_flat': 'in_playlist',
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        playlist_title = info['title']
        for entry in info['entries']:
            song_url = entry['url']
            title = entry['title']
            song = Song(song_url, title)
            queue.append(song)

    await ctx.send(f'Đã thêm thành công playlist {playlist_title} vào danh sách phát nhạc!')

async def play_song(ctx):
    global is_playing

    if len(queue) == 0 and ctx.voice_client:
        await ctx.send('Danh sách phát nhạc đã hết. Bạn hãy nhanh tay sử dụng !play để thêm nhạc vào danh sách và cùng thưởng thức với tôi nào!')
        is_playing = False
        return

    song = queue[0]
    save_queue.insert(0,queue[0])

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(song.url, download=False)
        url2 = info['formats'][0]['url']

        ctx.voice_client.play(discord.FFmpegPCMAudio(url2), after=lambda e: bot.loop.create_task(play_song(ctx)))

    await ctx.send(f'Đang phát: {song.title}')
    if repeat_mode:
        queue.insert(0,save_queue[0])
    if repeat_queue:
        queue.append(save_queue[1])
    queue.pop(0)
    is_playing = True

@bot.command(name="queue", aliases=["q"], help="Hiển thị danh sách phát nhạc")
async def q(ctx):
    if len(queue) == 0:
        await ctx.send('Danh sách phát nhạc rỗng.')
        return

    queue_list = '\n'.join([f'{index+1}. {song.title}' for index, song in enumerate(queue)])
    await ctx.send(f'Danh sách phát nhạc:\n{queue_list}')

@bot.command(name="repeat", aliases=["r"], help="Lặp lại 1 bài hoặc cả danh sách (a là 1 hoặc all). Muốn tắt nó chỉ việc *repeat")
async def repeat(ctx, mode=None):
    global repeat_mode
    global repeat_queue
    if mode == '1':
        if len(queue) == 0:
            queue.append(queue.pop())
        repeat_mode = True
        repeat_queue = False
        await ctx.send('Chế độ lặp phát 1 bài hát đã được bật!')
    elif mode == 'all':
        if len(queue) == 0:
            queue.append(queue.pop())
        repeat_mode = False
        repeat_queue = True
        await ctx.send('Chế độ lặp phát danh sách đã được bật!')
    else:
        repeat_mode = False
        repeat_queue = False
        await ctx.send('Chế độ lặp đã tắt!')

@bot.command(name="pause", help="Tạm dừng bài hát đang phát")
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send('Đã tạm dừng phát nhạc.')
    else:
        await ctx.send('Không có gì đang phát để tạm dừng.')

@bot.command(name="skip", aliases=["s"], help="Bỏ qua bài hát hiện tại")
async def skip(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send('Đang chuyển sang bài nhạc tiếp theo.')
    else:
        await ctx.send('Không có gì đang phát để chuyển bài.')

@bot.command(name = "resume", help="Tiếp tục bài hát đang phát")
async def resume(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send('Tiếp tục phát nhạc.')
    else:
        await ctx.send('Không có gì đang tạm dừng để tiếp tục.')

@bot.command(name="stop", help="Tắt phát nhạc và xóa danh sách phát nhạc")
async def stop(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()
        await ctx.send('Đã dừng phát nhạc.')
    else:
        await ctx.send('Không có gì đang phát để dừng.')
        
# Lệnh để ngắt kết nối bot với kênh thoại
@bot.command(name="leave", help="Rời khỏi phòng")
async def leave(ctx):
    # Kiểm tra xem bot có đang trong kênh thoại không
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        await ctx.send('Đã ngắt kết nối.')
        queue.clear()
        
@bot.command(name="Help", aliases=["h"], help="Dùng để hiển thị tất cả các lệnh của bot")
async def commands_command(ctx):
    command_prefix = bot.command_prefix
    embed = discord.Embed(title="Lệnh của bot và cách sử dụng", description="Dưới đây là danh sách các lệnh có sẵn:", color = discord.Color.blue())

    for command in bot.commands:
        if command.hidden:
            continue
        if command.brief:
            value = f"**{command.brief}**\n"
        else:
            value = ""

        value += f"Sử dụng: `{command_prefix}{command.name}`"
        if command.aliases:
            value += f"\nCó thể sử dụng thêm: `{command_prefix}{', '.join(command.aliases)}`"
        value += f"\nCông dụng: {command.help}"
        embed.add_field(name=command.name, value=value, inline=True)

    await ctx.send(embed=embed)


# Kết nối bot với Discord
bot.run('MTEwNzM2NDIwODc3OTIxMDc3Mg.GWVBJD.SygtSZCcQ-b_F1laeuEONQOO1AXEQ_We-JLnME')