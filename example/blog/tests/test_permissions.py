from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.template import Template, Context
from django.test import TestCase
from django.test.client import RequestFactory


import djadmin2
from djadmin2.models import ModelAdmin2
from djadmin2.permissions import TemplatePermissionChecker
from blog.models import Post


class TemplatePermissionTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User(
            username='admin',
            is_staff=True)
        self.user.set_password('admin')
        self.user.save()

    def render(self, template, context):
        template = Template(template)
        context = Context(context)
        return template.render(context)

    def test_permission_wrapper(self):
        model_admin = ModelAdmin2(Post, djadmin2.default)
        request = self.factory.get(reverse('admin2:blog_post_index'))
        request.user = self.user
        permissions = TemplatePermissionChecker(request, model_admin)
        context = {
            'permissions': permissions,
        }

        result = self.render(
            '{{ permissions.has_unvalid_permission }}',
            context)
        self.assertEqual(result, '')

        result = self.render('{{ permissions.has_add_permission }}', context)
        self.assertEqual(result, 'False')

        post_add_permission = Permission.objects.get(
            content_type__app_label='blog',
            content_type__model='post',
            codename='add_post')
        self.user.user_permissions.add(post_add_permission)
        # invalidate the users permission cache
        if hasattr(self.user, '_perm_cache'):
            del self.user._perm_cache

        result = self.render('{{ permissions.has_add_permission }}', context)
        self.assertEqual(result, 'True')

    def test_admin_traversal_by_name(self):
        post_add_permission = Permission.objects.get(
            content_type__app_label='blog',
            content_type__model='post',
            codename='add_post')
        self.user.user_permissions.add(post_add_permission)

        model_admin = ModelAdmin2(Post, djadmin2.default)
        request = self.factory.get(reverse('admin2:blog_post_index'))
        request.user = self.user
        permissions = TemplatePermissionChecker(request, model_admin)
        context = {
            'permissions': permissions,
        }

        result = self.render('{{ permissions.has_add_permission }}', context)
        self.assertEqual(result, 'True')
        result = self.render('{{ permissions.blog_post.has_add_permission }}', context)
        self.assertEqual(result, 'True')
        result = self.render('{{ permissions.blog_post.has_change_permission }}', context)
        self.assertEqual(result, 'False')
        result = self.render('{{ permissions.auth_user.has_delete_permission }}', context)
        self.assertEqual(result, 'False')

        result = self.render(
            '{{ permissions.unknown_app.has_add_permission }}',
            context)
        self.assertEqual(result, '')

        result = self.render(
            '{{ permissions.blog_post.has_unvalid_permission }}',
            context)
        self.assertEqual(result, '')

    def test_admin_binding(self):
        user_admin = djadmin2.default.get_admin_by_name('auth_user')
        post_admin = djadmin2.default.get_admin_by_name('blog_post')
        request = self.factory.get(reverse('admin2:auth_user_index'))
        request.user = self.user
        permissions = TemplatePermissionChecker(request, user_admin)

        post = Post.objects.create(title='Hello', body='world')
        context = {
            'post': post,
            'post_admin': post_admin,
            'permissions': permissions,
        }

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions|for_admin:post_admin }}',
            context)
        self.assertEqual(result, '')

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission }}'
            '{% with permissions|for_admin:post_admin as permissions %}'
                '{{ permissions.has_add_permission }}'
            '{% endwith %}',
            context)
        self.assertEqual(result, 'FalseFalse')

        post_add_permission = Permission.objects.get(
            content_type__app_label='blog',
            content_type__model='post',
            codename='add_post')
        self.user.user_permissions.add(post_add_permission)
        # invalidate the users permission cache
        if hasattr(self.user, '_perm_cache'):
            del self.user._perm_cache

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission }}'
            '{% with permissions|for_admin:post_admin as permissions %}'
                '{{ permissions.has_add_permission }}'
            '{% endwith %}'
            '{{ permissions.blog_post.has_add_permission }}',
            context)
        self.assertEqual(result, 'FalseTrueTrue')

    def test_object_level_permission(self):
        model_admin = ModelAdmin2(Post, djadmin2.default)
        request = self.factory.get(reverse('admin2:blog_post_index'))
        request.user = self.user
        permissions = TemplatePermissionChecker(request, model_admin)

        post = Post.objects.create(title='Hello', body='world')
        context = {
            'post': post,
            'permissions': permissions,
        }

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_unvalid_permission|for_object:post }}',
            context)
        self.assertEqual(result, '')

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission|for_object:post }}',
            context)
        self.assertEqual(result, 'False')

        post_add_permission = Permission.objects.get(
            content_type__app_label='blog',
            content_type__model='post',
            codename='add_post')
        self.user.user_permissions.add(post_add_permission)
        # invalidate the users permission cache
        if hasattr(self.user, '_perm_cache'):
            del self.user._perm_cache

        # object level permission are not supported by default. So this will
        # return ``False``.
        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission }}'
            '{{ permissions.has_add_permission|for_object:post }}',
            context)
        self.assertEqual(result, 'TrueFalse')

        # binding an object and then checking for a specific view also works
        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission }}'
            '{% with permissions|for_object:post as permissions %}'
                '{{ permissions.has_add_permission }}'
            '{% endwith %}',
            context)
        self.assertEqual(result, 'TrueFalse')
