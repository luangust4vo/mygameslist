from django.contrib import admin
from .models import Game, Genre, Platform, UserGameList, Review, Activity

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'rawg_id')
    search_fields = ('name',)

@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'rawg_id')
    search_fields = ('name',)

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('title', 'release_date', 'rawg_rating', 'local_rating')
    search_fields = ('title',)
    filter_horizontal = ('genres', 'platforms')

@admin.register(UserGameList)
class UserGameListAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'status', 'date_added', 'date_updated')
    list_filter = ('status',)
    search_fields = ('user__username', 'game__title')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'rating', 'title', 'created_at')
    list_filter = ('rating',)
    search_fields = ('user__username', 'game__title')

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'action', 'detail', 'created_at')
    list_filter = ('action',)
    search_fields = ('user__username', 'game__title')