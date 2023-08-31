import os
from dotenv import load_dotenv
from isodate import parse_duration
import googleapiclient.discovery
import googleapiclient.errors
import pandas as pd
import matplotlib.pyplot as plt

load_dotenv()

def get_channel_statistics(youtube,KORTY_CHANNEL_ID):
    request = youtube.channels().list(
        id=KORTY_CHANNEL_ID,
        part="statistics,snippet,contentDetails"
    )
    channel_statistics = request.execute()
    return channel_statistics

def plot_channel_details(channel_statistics):
    
    if channel_statistics is None:
        get_channel_statistics()
    
    # Extract the channel statistics
    channel_title = channel_statistics["items"][0]["snippet"]["title"]
    subscribers = channel_statistics["items"][0]["statistics"]["subscriberCount"]
    video_count = channel_statistics["items"][0]["statistics"]["videoCount"]
    view_count = channel_statistics["items"][0]["statistics"]["viewCount"]

    data = {
        'Subscribers': [subscribers],
        'Number of videos': [video_count],
        'Total views': [view_count]
    }
    
    # Convert them to a DataFrame and plot
    df = pd.DataFrame(data, index=[channel_title])
    df['Subscribers'] = df['Subscribers'].astype(int)
    df['Number of videos'] = df['Number of videos'].astype(int)
    df['Total views'] = df['Total views'].astype(int)
    
    df.to_excel('channel_statistics.xlsx', sheet_name='Channel Statistics',index=False)
    
def get_channels_video_ids(youtube,playlist_id): #gets all the video ids of the channel
    
    video_ids = []
    request = youtube.playlistItems().list(
        playlistId=playlist_id,
        part="snippet,contentDetails",
        maxResults=50
    )

    response = request.execute()

    for video in response["items"]: #gets the first 50 videos
        video_ids.append(video["contentDetails"]["videoId"])

    while "nextPageToken" in response: #gets the rest of the videos
        request = youtube.playlistItems().list(
            playlistId=playlist_id,
            part="snippet,contentDetails",
            maxResults=50,
            pageToken=response["nextPageToken"]
        )
        response = request.execute()
        for video in response["items"]:
            video_ids.append(video["contentDetails"]["videoId"])

    return video_ids
    

def get_playlist_details(youtube,video_ids,playlist_title):

    video_titles = []
    video_view_counts = []
    video_like_counts = []
    video_favourite_counts = []
    video_comment_counts = []
    video_duration_minutes = []

    for video_id in video_ids: #gets the details of each video
        request = youtube.videos().list(
            part="snippet,contentDetails,statistics,topicDetails",
            id=video_id
        )

        response = request.execute()
        
        title = response["items"][0]["snippet"].get("title", "NA")
        view_count = response["items"][0]["statistics"].get("viewCount", 0)
        like_count = response["items"][0]["statistics"].get("likeCount", 0)
        favorite_count = response["items"][0]["statistics"].get("favoriteCount", 0)
        comment_count = response["items"][0]["statistics"].get("commentCount", 0)
        
        video_titles.append(title)
        video_view_counts.append(view_count)
        video_like_counts.append(like_count)
        video_favourite_counts.append(favorite_count)
        video_comment_counts.append(comment_count)

        #Fetch the video duration and convert it to minutes.
        duration = response["items"][0]["contentDetails"].get("duration", "PT0M0S")
        parsed_duration = parse_duration(duration)
        duration_in_minutes = parsed_duration.total_seconds() / 60.0
        
        video_duration_minutes.append(duration_in_minutes)

    data = {
        'Video title': video_titles,
        'View count': list(map(int, video_view_counts)),  # Convert to integers
        'Like count': list(map(int, video_like_counts)),  # Convert to integers
        'Comment count': list(map(int, video_comment_counts)),  # Convert to integers
        'Favourite count': list(map(int, video_favourite_counts))  # Convert to integers
    }

    df = pd.DataFrame(data)


    #Group videos into duration ranges (e.g., 35-40 mins).
    bins = [0, 5, 10, 15, 20, 25, 30, 35, 40]  # Adjust bins as needed
    labels = ['0-5', '5-10', '10-15', '15-20', '20-25', '25-30', '30-35', '35-40']
    df['Duration Group'] = pd.cut(video_duration_minutes, bins=bins, labels=labels, right=False)


    #Calculate the percentage of total channel views for each group.
    total_views = df['View count'].astype(int).sum()
    group_by_duration = df.groupby('Duration Group')['View count'].sum().reset_index(name='Total Views')
    group_by_duration['Percentage of Total Views'] = (group_by_duration['Total Views'] / total_views) * 100
    
    # Plotting
    plt.bar(group_by_duration['Duration Group'], group_by_duration['Percentage of Total Views'])
    plt.xlabel('Video Duration (mins)')
    plt.ylabel('Percentage of Total Views')
    plt.title(f'Video Duration vs. Percentage of Total Views For {playlist_title}')
    plt.savefig(f'{playlist_title} Duration vs. Percentage of Total Views.png')
    plt.show()

    total_views = sum(map(int, video_view_counts))
    total_likes = sum(map(int, video_like_counts))
    total_comments = sum(map(int, video_comment_counts))
    total_favourites = sum(map(int, video_favourite_counts))

    # Calculate the average view to like ratio,average view to comment ratio and average view to favourite ratio
    try:
        average_view_to_like_ratio = int(total_views / total_likes)
    except ZeroDivisionError:
        average_view_to_like_ratio = 0

    try:
        average_view_to_comment_ratio = int(total_views / total_comments)
    except ZeroDivisionError:
        average_view_to_comment_ratio = 0

    try:
        average_view_to_favorite_ratio = int(total_views / total_favourites)
    except ZeroDivisionError:
        average_view_to_favorite_ratio = 0
    
    df.to_excel(f'{playlist_title} Statistics.xlsx', sheet_name=f'{playlist_title}',index=False)
    df1 = pd.DataFrame({
        'Metric': ['Average view to like ratio', 'Average view to comment ratio', 'Average view to favourite ratio'],
        'Value': [average_view_to_like_ratio, average_view_to_comment_ratio, average_view_to_favorite_ratio]
    })
    df1.to_excel(f'{playlist_title} Average Ratios Statistics.xlsx', sheet_name='Average Ratios',index=False)
    return {'Average view to like ratio': average_view_to_like_ratio, 'Average view to comment ratio': average_view_to_comment_ratio, 'Average view to favourite ratio': average_view_to_favorite_ratio}

def get_playlists_id(youtube,KORTY_CHANNEL_ID):
    playlist_ids = {}
    request = youtube.playlists().list(
            part="snippet,contentDetails,id",
            channelId=KORTY_CHANNEL_ID,
            maxResults=25
        )
    response = request.execute()
    for i in response['items']:
        if i['snippet']['title'] == 'FLOW, WITH KORTY' or i['snippet']['title'] == 'LOVE OR LIES':
            playlist_ids[i['snippet']['title']] = i['id']
        
    return playlist_ids  

def main():
    KORTY_CHANNEL_ID = "UCTFFhYhkLkxjhcCdwUKmQ5g"
    api_service_name = "youtube"
    api_version = "v3"

    youtube = googleapiclient.discovery.build( 
        api_service_name, api_version, developerKey=os.getenv("GOOGLE_API_KEY"))   
    
    channel_statistics = get_channel_statistics(youtube,KORTY_CHANNEL_ID)
    plot_channel_details(channel_statistics)
    uploads_playlist_id = channel_statistics["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    playlist_ids = get_playlists_id(youtube,KORTY_CHANNEL_ID)
    playlist_ids['All Uploads'] = uploads_playlist_id
    print(playlist_ids)

    for playlist_id in playlist_ids:
        video_ids = get_channels_video_ids(youtube,playlist_ids[playlist_id])
        stats = get_playlist_details(youtube,video_ids,playlist_id)
        print(stats)

main()