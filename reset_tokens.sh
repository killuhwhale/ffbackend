while true; 
  do sudo docker compose exec instafitapiprod python manage.py reset_tokens; 
  sleep $(python3 -c 'print(60*60*24)'); 
done
