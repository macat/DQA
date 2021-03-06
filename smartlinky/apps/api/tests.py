from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson as json

from apps.core.models import Link, Section, Page
from apps.core.tests import create_sample_documentation, create_sample_page, create_sample_section, create_sample_link, \
    SAMPLE_DOCUMENTATIONS, SAMPLE_PAGES, SAMPLE_SECTIONS, SAMPLE_LINKS

from apps.core.models import Link


# TODO: docstrings
class APITest(TestCase):
    
    def setUp(self):
        self.page1 = create_sample_page(**SAMPLE_PAGES['pythondocs_builtins'])
        self.page2 = create_sample_page(**SAMPLE_PAGES['pythondocs_intro'])
        self.page3 = create_sample_page(**SAMPLE_PAGES['pythondocs_logging'])
        self.section1 = create_sample_section(self.page1, **SAMPLE_SECTIONS['pythondocs_builtins_built-in-functions'])
        self.section2 = create_sample_section(self.page1, **SAMPLE_SECTIONS['pythondocs_builtins_non-essential-built-in-functions'])
        self.section3 = create_sample_section(self.page3, **SAMPLE_SECTIONS['pythondocs_logging_configuration_functions'])
        self.link1 = create_sample_link(self.section1, **SAMPLE_LINKS['link1'])
        self.link2 = create_sample_link(self.section1, **SAMPLE_LINKS['link2'])
        self.link3 = create_sample_link(self.section2, **SAMPLE_LINKS['link3'])
    
    def get(self, data={}, *args, **kwargs):
        response = self.client.get(self.path, data, *args, **kwargs)
        # HACK: read above def refresh_objects(self)
        self.refresh_objects()
        return response

    def post(self, data, *args, **kwargs):
        response = self.client.post(self.path, data, *args, **kwargs)
        # HACK: read above def refresh_objects(self)
        self.refresh_objects()
        return response
    
    # TODO: investigate and fix the issue with objects not being fetched from db
    #    steps to reproduce:
    #    1. remove self.refresh_objects() from def post(self, data, *args, **kwargs)
    #    2. remove self.refresh_objects() from def get(self, data={}, *args, **kwargs)
    #    3. run tests for the 'api' app
    def refresh_objects(self):
        try:
            self.page1 = Page.objects.get(pk=self.page1.pk)
            self.page2 = Page.objects.get(pk=self.page2.pk)
            self.page3 = Page.objects.get(pk=self.page3.pk)
            self.section1 = Section.objects.get(pk=self.section1.pk)
            self.section2 = Section.objects.get(pk=self.section2.pk)
            self.section3 = Section.objects.get(pk=self.section3.pk)
            self.link1 = Link.objects.get(pk=self.link1.pk)
            self.link2 = Link.objects.get(pk=self.link2.pk)
            self.link3 = Link.objects.get(pk=self.link3.pk)
        except:
            # probably some were removed
            pass

# TODO: docstrings
class InitAPITest(APITest):
    
    def setUp(self):
        self.path = reverse('api_init')
        super(InitAPITest, self).setUp()
        
    def testUnknownUrl(self):
        kwargs = {'url': 'http://google.com'}
        response = self.get(kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, json.dumps({'sections':{}}))
                         
    def testPageWithoutLinks(self):
        kwargs = {'url': self.page2.url}
        response = self.get(kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, json.dumps({'sections':{}}))
        
    def testSectionsWithLinks(self):
        kwargs = {'url': self.page1.url}
        response = self.get(kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, json.dumps({
            'sections':{
                self.section1.html_id: self.section1.links.count(), 
                self.section2.html_id: self.section2.links.count(),
            },
        }))
        
# TODO: docstrings
class UsersLinksAPITest(APITest):
    
    def setUp(self):
        self.path = reverse('api_users_links')
        super(UsersLinksAPITest, self).setUp()
        
    def testUnknownUrl(self):
        kwargs = {
            'url': 'http://google.com',
            'section_id': 'foo',
        }
        response = self.get(kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, json.dumps({'links':[]}))
                         
    def testUnknownSection(self):
        kwargs = {
            'url': self.page2.url,
            'section_id': 'foo',
        }
        response = self.get(kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, json.dumps({'links':[]}))
        
    def testSectionWithoutLinks(self):
        kwargs = {
            'url': self.section3.page.url,
            'section_id': self.section3.html_id,
        }
        response = self.get(kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, json.dumps({'links':[]}))
    
    def testSectionWithLinks(self):
        kwargs = {
            'url': self.section2.page.url,
            'section_id': self.section2.html_id,
        }
        response = self.get(kwargs)
        links = []
        for link in self.section2.links.all():
            links.append({
                'id': link.id,
                'url': link.url,
                'title': link.title,
                'is_relevant': link.is_relevant,
                'up_votes': link.up_votes,
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, json.dumps({
            'links': links
        }))
           
    def testOrder(self):
        kwargs = {
            'url': self.section2.page.url,
            'section_id': self.section2.html_id,
        }
        response = self.get(kwargs)
        links = []
        for link in self.section2.links.all().order_by('-up_votes'):
            links.append({
                'id': link.id,
                'url': link.url,
                'title': link.title,
                'is_relevant': link.is_relevant,
                'up_votes': link.up_votes,
            })
        self.assertEqual(response.status_code, 200)
        content_json = json.loads(response.content)
        json_links = content_json['links']
        self.assertEqual(links, json_links)
        
# TODO: docstrings
class AddLinkAPITest(APITest):
    def setUp(self):
        self.path = reverse('api_add_link')
        super(AddLinkAPITest, self).setUp()

    def testWrongUrl(self):
        Link.objects.all().delete()
        kwargs = {
            'link_url': 'BAD',
            'url': 'http://www.wabidesign.it',
            'page_title': 'Test',
            'section_id': 'test',
            'section_title': 'Test htm',
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual('message' in content_json, True)
        self.assertEqual(Link.objects.all().count(), 0)

    def testMissingArguments(self):
        kwargs = {
            'link_url': 'http://www.wabidesign.it/',
            'url': 'http://example.com',
            'section_id': 'test',
            'section_title': 'Test htm',
        }
        response = self.post(kwargs)
        self.assertEqual(response.status_code, 400)
    
        kwargs = {
            'link_url': 'http://www.wabidesign.it/',
            'url': 'http://example.com',
            'page_title': 'Test',
            'section_title': 'Test htm',
        }
        response = self.post(kwargs)
        self.assertEqual(response.status_code, 400)

        kwargs = {
            'link_url': 'http://www.wabidesign.it/',
            'url': 'http://example.com',
            'page_title': 'Test',
            'section_id': 'test',
        }
        response = self.post(kwargs)
        self.assertEqual(response.status_code, 400)

    def testSimpleUrl(self):
        Link.objects.all().delete()
        kwargs = {
            'link_url': 'http://www.wabidesign.it/',
            'url': 'http://example.com',
            'page_title': 'Test',
            'section_id': 'test',
            'section_title': 'Test htm',
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual('Antonella Tezza' in content_json['title'], True)
        self.assertEqual(Link.objects.all().count(), 1)

    def testMoreUrls(self):
        Link.objects.all().delete()
        kwargs = {
            'link_url': 'http://virtuallight.pl/',
            'url': 'http://example.com',
            'page_title': 'Test',
            'section_id': 'test',
            'section_title': 'Test htm',
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual('things' in content_json['title'], True)
        kwargs = {
            'link_url': 'http://attila.maczak.hu/',
            'url': 'http://example.com',
            'page_title': 'Test',
            'section_id': 'test',
            'section_title': 'Test htm',
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual('Attila' in content_json['title'], True)
        self.assertEqual(Link.objects.all().count(), 2)

# TODO: docstrings
class QALinksAPITest(APITest):
    
    def setUp(self):
        self.path = reverse('api_qa_links')
        super(QALinksAPITest, self).setUp()
        
    def testCache(self):
        kwargs = {
            'url': self.section1.page.url,
            'page_title': self.section1.page.meta_title,
            'section_id': self.section1.html_id,
            'section_title': self.section1.html_title,
        }
        response = self.get(kwargs)
        self.assertEqual(response.status_code, 200)
        links = cache.get(self.section1.cache_key)
        self.assertNotEquals(links, None)
        
# TODO: docstrings
class VoteUpAPITest(APITest):
    
    def setUp(self):
        self.path = reverse('api_vote_up')
        super(VoteUpAPITest, self).setUp()
    
    def testNotIntegerId(self):
        kwargs = {
            'id': 'foo',
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual('message' in content_json, True)
        
    def testIncrementUpVotes(self):
        up_votes = self.link1.up_votes
        kwargs = {
            'id': self.link1.id,
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.link1.up_votes, up_votes + 1)
                  
    def testNoLink(self):
        link_id = self.link1.id
        Link.objects.all().delete()
        kwargs = {
            'id': link_id,
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual('message' in content_json, True)
              
# TODO: docstrings
class SetRelevantAPITest(APITest):
    
    def setUp(self):
        self.path = reverse('api_set_relevant')
        super(SetRelevantAPITest, self).setUp()
    
    def testNotIntegerId(self):
        kwargs = {
            'id': 'foo',
            'is_relevant': 1,
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual('message' in content_json, True)
        
    def testNotValidIsRelevant(self):
        kwargs = {
            'id': self.link1.id,
            'is_relevant': 'foo',
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual('message' in content_json, True)

    def testSetRelevantTrue(self):
        kwargs = {
            'id': self.link1.id,
            'is_relevant': 1,
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.link1.is_relevant, True)
        kwargs = {
            'id': self.link2.id,
            'is_relevant': 1,
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.link2.is_relevant, True)

    def testSetRelevantFalse(self):
        kwargs = {
            'id': self.link1.id,
            'is_relevant': 0,
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.link1.is_relevant, False)
        kwargs = {
            'id': self.link2.id,
            'is_relevant': 0,
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.link2.is_relevant, False)      
          
    def testNoLink(self):
        link_id = self.link1.id
        Link.objects.all().delete()
        kwargs = {
            'id': link_id,
            'is_relevant': 1,
        }
        response = self.post(kwargs)
        content_json = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual('message' in content_json, True)        