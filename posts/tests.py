from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, Client

from posts.models import Post, Comment, Follow


class TestProfile(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="sarah",
                                             email="connor.s@skynet.com",
                                             password="12345")
        self.post = Post.objects.create(
            text="You're talking about things "
                 "I haven't done yet in the past tense. "
                 "It's driving me crazy!",
            author=self.user)
        self.client.force_login(self.user)

    def test_profile(self):
        response = self.client.get("/sarah/")
        self.assertEqual(response.status_code, 200)  # страница profile существует
        self.assertEqual(response.context['count'], 1)  # проверка что запись 1,
        # авторизованный пользователь может опубликовать пост
        self.assertIsInstance(response.context["prof_user"], User)  # автор это экземпляр класса User
        self.assertEqual(response.context["prof_user"].username,
                         self.user.username)  # автор страницы profile это пользователь, который авторизирован.
        self.assertEqual(response.context["page"][0].text, self.post.text)
        # После публикации поста новая запись появляется на персональной странице profile

    def test_index(self):
        response = self.client.get('')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context["page"][0].text), self.post.text)
        # После публикации поста новая запись появляется на странице index

    def test_post_id(self):
        response = self.client.get(f"/sarah/{self.post.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["post"].text, self.post.text)
        # После публикации поста новая запись появляется на отдельной странице post

    def test_post_edit(self):
        response = self.client.get(f"/sarah/{self.post.id}/edit/", follow=True)
        self.assertEqual(response.status_code, 200)
        post_edit = {'text': "Я изменен", "author": self.user}
        self.client.post(f"/sarah/{self.post.id}/edit/", post_edit, follow=True)
        response = self.client.get(f"/sarah/{self.post.id}/")
        self.assertEqual(response.context["post"].text, post_edit['text'])
        response = self.client.get('')
        self.assertEqual(str(response.context["page"][0].text), post_edit['text'])
        response = self.client.get("/sarah/")
        self.assertEqual(str(response.context["page"][0].text), post_edit['text'])
        # Авторизованный пользователь может отредактировать свой пост и его содержимое изменится на всех связанных страницах

    def test_user_not_auth(self):
        self.client.logout()
        response = self.client.get(f"/new/", follow=True)
        self.assertEqual(response.redirect_chain, [('/auth/login/?next=/new/', 302)])
        # Неавторизованный посетитель не может опубликовать пост (его редиректит на страницу входа)

    def test_not_found(self):
        response = self.client.get(f"/new123/", follow=True)
        self.assertEqual(response.status_code, 404)

    def test_image(self):
        with open('media/posts/file.png', 'rb') as img:
            self.client.post(f"/sarah/{self.post.id}/edit/",
                             {'author': self.user, 'text': 'post with image', 'image': img})
            response = self.client.get(f"/sarah/{self.post.id}/")
            self.assertEqual(response.context["post"].text, 'post with image')
            self.assertContains(response, '<img')

            response = self.client.get(f"/sarah/")
            self.assertContains(response, '<img')

            cache.clear()
            response = self.client.get('')
            self.assertContains(response, 'post with image')

    def test_not_image(self):
        with open('media/posts/No_image.py', 'rb') as img:
            self.client.post(f"/sarah/{self.post.id}/edit/",
                             {'author': self.user, 'text': 'post with not image', 'image': img})
            response = self.client.get(f"/sarah/{self.post.id}/")
            self.assertNotContains(response, 'post with not image')
            self.assertEqual(Post.objects.count(), 1)

    def test_cache_index(self):
        self.client.post(f"/new/",
                         {'author': self.user, 'text': 'test before cache'})
        response = self.client.get('')
        self.assertContains(response, 'test before cache')
        self.client.post(f"/new/",
                         {'author': self.user, 'text': 'test cache'})
        response = self.client.get('')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'test cache')
        cache.clear()
        response = self.client.get('')
        self.assertContains(response, 'test cache')


class TestFollow(TestCase):
    def setUp(self):
        self.client_follower = Client()
        self.client_following = Client()
        self.user_follower = User.objects.create_user(username="sarah",
                                                      email="connor.s@skynet.com",
                                                      password="12345")

        self.user_following = User.objects.create_user(username="masha",
                                                       email="masha.s@skynet.com",
                                                       password="12345")
        self.post = Post.objects.create(
            text="You're talking about things "
                 "I haven't done yet in the past tense. "
                 "It's driving me crazy!",
            author=self.user_following)

        self.client_follower.force_login(self.user_follower)
        self.client_following.force_login(self.user_following)

    def test_user_is_follower(self):
        response = self.client_follower.get(f"/{self.user_following.username}/follow/", follow=True)
        self.assertEqual(response.status_code, 200)
        response = self.client_follower.get(f"/follow/")
        self.assertEqual(str(response.context["page"][0].text), self.post.text)
        response = self.client_follower.get(f"/{self.user_following.username}/unfollow/", follow=True)
        self.assertEqual(response.status_code, 200)
        response = self.client_following.get(f"/follow/")
        self.assertNotContains(response, self.post.text)

    def test_auth_comment(self):
        self.client_follower.post(f"/{self.user_following.username}/{self.post.id}/comment/",
                                  {'author': self.user_follower, 'text': 'Comment from follower'})
        response = self.client_follower.get(f"/{self.user_following.username}/{self.post.id}/")
        self.assertContains(response, 'Comment from follower')
        # Запрос от неваторизированого пользователя client
        response = self.client.get(f"/{self.user_following.username}/{self.post.id}/comment/", follow=True)
        self.assertEqual(response.redirect_chain,
                         [(f'/auth/login/?next=/{self.user_following.username}/{self.post.id}/comment/', 302)])
