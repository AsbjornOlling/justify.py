<!DOCTYPE html>
<!-- Displays playlist from mpd -->

<html>
	<head>
		<meta charset="utf-8">
		<title>DAKKEDAK</title>
		<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
		<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
		<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">

	</head>
	<body>
		<div class="container">
			<h>Playlist</h>
			<table class="table table-striped">
				<thead>
					<tr>
						<th>Song</th>
						<th>Artist</th>
						<th>Time</th>
						<th>Votes</th>
					</tr>
				</thead>
				<tbody>
				% for song in plist:
					<tr>
					  <td>
							% if song["pos"] == "0":
								<span class="fa fa-play"></span>
						  % end
						{{song["title"]}}</td>
						<td>{{song["artist"]}}</td>
						<td>{{int(song["time"]) / 60}}:{{str(int(song["time"]) % 60).zfill(2)}}</td>
						<td>
							<form action="/list" method="post"> 
								<input type="hidden" name="voteID" value="{{song["id"]}}"> 
								<button class="btn btn-default" type="submit"><span class="fa fa-thumbs-up"></span> {{votes[song["id"]]}}</button>
							</form>
						</td>
					</tr>
				% end
				</tbody>
			</table>
			<div class="input-group">
				<form action="/search" method="post">
					<input class="form-control" name="inputany" type="text" />
					<span class="input-group-btn">
						<button class="btn btn-default" value="FIND DIT DAK!" type="submit"><span class="fa fa-search"></span></button>
					</span>
				</form>
			</div>
		</div> <!-- /container -->
	</body>
</html>
