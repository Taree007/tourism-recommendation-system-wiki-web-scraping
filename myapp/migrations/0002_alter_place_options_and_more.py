# Generated by Django 5.2.1 on 2025-05-25 20:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='place',
            options={'ordering': ['-relevance_score']},
        ),
        migrations.RenameField(
            model_name='place',
            old_name='pagerank_score',
            new_name='relevance_score',
        ),
        migrations.RemoveField(
            model_name='place',
            name='categories',
        ),
        migrations.AddField(
            model_name='place',
            name='category_count',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='place',
            name='date_created',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date created'),
        ),
        migrations.AddField(
            model_name='place',
            name='language_links',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='place',
            name='linkshere',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='place',
            name='number_of_categories',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of Categories'),
        ),
        migrations.AddField(
            model_name='place',
            name='number_of_external_links',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of External Links'),
        ),
        migrations.AddField(
            model_name='place',
            name='number_of_images',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of Images'),
        ),
        migrations.AddField(
            model_name='place',
            name='number_of_languages',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of Languages'),
        ),
        migrations.AddField(
            model_name='place',
            name='number_of_links',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of Links'),
        ),
        migrations.AddField(
            model_name='place',
            name='number_of_references',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of References'),
        ),
        migrations.AddField(
            model_name='place',
            name='number_of_sections',
            field=models.IntegerField(blank=True, null=True, verbose_name='Number of Sections'),
        ),
        migrations.AddField(
            model_name='place',
            name='page_length',
            field=models.IntegerField(blank=True, null=True, verbose_name='Page Length'),
        ),
        migrations.AddField(
            model_name='place',
            name='revision_count',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='place',
            name='title',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='place',
            name='total_links',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='place',
            name='page_views',
            field=models.IntegerField(blank=True, null=True, verbose_name='Page Views'),
        ),
        migrations.AlterField(
            model_name='place',
            name='wikipedia_link',
            field=models.URLField(blank=True, verbose_name='Link'),
        ),
        migrations.AlterField(
            model_name='placeimage',
            name='image_url',
            field=models.URLField(verbose_name='Image link'),
        ),
        migrations.CreateModel(
            name='PlaceCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.category')),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.place')),
            ],
            options={
                'verbose_name_plural': 'Place Categories',
                'unique_together': {('place', 'category')},
            },
        ),
        migrations.DeleteModel(
            name='SimilarPlace',
        ),
    ]
