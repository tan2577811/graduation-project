# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import codecs
import json
import pymysql
import pymysql.cursors
import pymongo

from scrapy.conf import settings
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exporters import JsonItemExporter
from twisted.enterprise import adbapi
from .items import ZhipinItem
from scrapy import log

class ArticlespiderPipeline(object):
    def process_item(self, item, spider):
        return item

# class JsonWithEncodingPipeline(object):
#     # 自定义Json文件的导出
#     def __init__(self):
#         self.file = codecs.open('article.json', 'w', encoding="utf-8")
#
#     def process_item(self, item, spider):
#         lines = json.dumps(dict(item), ensure_ascii=False) + "\n"
#         self.file.write(lines)
#         return item
#
#     def close_spider(self, spider):
#         self.file.close()
#
# class MysqlPipeline(object):
#     def __init__(self):
#         self.conn = pymysql.connect(host='127.0.0.1', port=3306,  user='root',  password='2577811', db='article_spider', charset='utf8', use_unicode = True)
#         self.cur = self.conn.cursor()
#
#     def process_item(self, item, spider):
#
#         insert_sql = """INSERT INTO jobbole_data(title, url, url_object_id, create_date, front_image_url, praise_nums, fav_nums, comment_nums, content, tags, front_image_path)VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s,%s )"""
#
#         self.cur.execute(insert_sql, (item['title'], item['url'], item['url_object_id'], item['create_date'], item['front_image_url'],item['front_image_path'], item['praise_nums'], item['fav_nums'], item['comment_nums'], item['content'], item['tags'] ))
#         self.conn.commit()

class MysqlTwistedPipeline(object):
    def __init__(self, dbpool):
        self.dbpool = dbpool


    @classmethod
    def from_settings(cls, settings):
        dbparms=dict(host=settings['MYSQL_HOST'],
                     db=settings['MYSQL_DBNAME'],
                     user=settings['MYSQL_USER'],
                     password=settings['MYSQL_PASSWORD'],
                     port=settings['MYSQL_PORT'],
                     charset='utf8',
                     cursorclass=pymysql.cursors.DictCursor,
                     use_unicode=True
                     )
        dbpool = adbapi.ConnectionPool('pymysql', **dbparms)
        return cls(dbpool)

    def process_item(self, item, spider):
        # 使用twisted将mysql插入变成异步执行
        query = self.dbpool.runInteraction(self.do_insert, item)
        query.addErrback(self.handle_error, item, spider)#处理异常

    def handle_error(self, failure, item, spider):
        # 处理异步插入的异常
        print(failure)

    def do_insert(self, cursor, item):
        # 执行具体的插入
        insert_sql, params = item.get_insert_sql()
        cursor.execute(insert_sql, params)

# class JsonExporterPipeline(object):
#     # 调用scrapy提供的json export 导出json文件
#     def __init__(self):
#         self.file = open('articleexport.json', 'wb')
#         self.exporter = JsonItemExporter(self.file, encoding='utf-8', ensure_ascii=False)
#         self.exporter.start_exporting()
#
#     def close_spider(self, spider):
#         self.exporter.finish_exporting()
#         self.file.close()
#
#     def process_item(self, item, spider):
#         self.exporter.export_item(item)
#         return item
class MongoDBPipleline(object):
    def __init__(self):
        self.client = pymongo.MongoClient(host=settings["MONGODB_HOST"],port=settings["MONGODB_PORT"])
        self.db = self.client[settings["MONGODB_DBNAME"]]
        self.coll = self.db[settings['MONGODB_COLL']]

    def process_item(self, item, spider):
        postItem = dict(item)
        self.coll.insert(postItem)
        return item


class ArticleImagePipeline(ImagesPipeline):
    def item_completed(self, results, item, info):
        if "front_image_url" in item:
            for ok, value in results:
                image_file_path = value["path"]
                item['front_image_path'] = image_file_path
                return item


class ElasticsearchPipeline(object):
    # 将数据写入到es中

    def process_item(self, item, spider):
        # 将item转换为es的数据
        item.save_to_es()

        return item