import os
import sys
import cherrypy
import logging
import time

import splunk, splunk.util
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.appserver.mrsparkle.lib.util as app_util
import splunk.appserver.mrsparkle.lib.paginator as paginator

path = os.path.join(app_util.get_apps_dir(), __file__.split('.')[-2], 'bin')
if not path in sys.path:
    sys.path.append(path)

from HadoopConnect.models.export import HDFSExport
from HadoopConnect.models.cluster import Cluster

logger = logging.getLogger('splunk')

class HDFSExportController(controllers.BaseController):
    '''Hadoop Export Jobs  Setup Controller'''

    def getNewHDFSExport(self, app, user):
        #this is a workaround for external REST handlers not supporting _new
        id = HDFSExport.build_id('_new_ext', app, user)
        h = HDFSExport.get(id)
        h.name = ''
        return h

    @expose_page(must_login=True, methods=['GET'])
    @route('/:action=create', methods=['GET'])
    def create(self, action, **kwargs):
        '''Form to add a new HDFS Export Job'''
        app = cherrypy.request.path_info.split('/')[3]
        user = cherrypy.session['user']['name']
        search = kwargs.get('search','')
        exportJob = self.getNewHDFSExport(app, user)
        clusters = Cluster.all().filter_by_app(app)
        return self.render_template('/%s:/templates/create_export_job.html' % app, dict(form_content='fomasdafe', app=app, search=search, exportJob=exportJob, clusters=clusters))

    @expose_page(must_login=True, methods=['GET'])
    @route('/:action=list', methods=['GET'])
    def list(self, action, **kwargs):
        ''' show the setup page '''
        return self.renderList(**kwargs)

    def renderList(self, exportJob=None, listErrors = None, **kwargs):
        offset      = int(kwargs.get('offset', 0))
        count       = int(kwargs.get('count', 10))

        app = cherrypy.request.path_info.split('/')[3]
        user = cherrypy.session['user']['name']

        user = cherrypy.session['user']['name']
        exportJobs = HDFSExport.all().filter_by_app(app)
        exportJobs._count_per_req = count

        # paginator
        pager = paginator.Google(exportJobs.get_total(), max_items_page=count, item_offset=offset)

        exportJob = exportJob or self.getNewHDFSExport(app, user)

        clusters = Cluster.all().filter_by_app(app)

        template_args = dict(form_content='form_content',
                             app=app,
                             exportJobs = exportJobs,
                             pager = pager,
                             offset = offset,
                             count = count,
                             exportJob = exportJob,
                             listErrors = listErrors,
                             clusters = clusters
                             )
        return self.render_template('/%s:/templates/list_hdfs_jobs.html' % app, template_args)


    @expose_page(must_login=True, methods=['POST'])
    @route('/:action=submitREDModal', methods=['POST'])
    def submitREDModal(self, action, **kwargs):
        '''accept a post of the information needed to create a HDFS Export Job'''
        user = cherrypy.session['user']['name']
        app = cherrypy.request.path_info.split('/')[3]

        successfullSave, exportJob = self.saveRED(user, app, **kwargs)
        if not successfullSave:
            logger.error("Could not save export job: %s" % exportJob.errors)
            search = kwargs.get('search','default')
            logger.info("export search: %s" % search)
            clusters = Cluster.all().filter_by_app(app)
            return self.render_template('/%s:/templates/create_export_job.html' % app, dict(form_content='fomasdafe', app=app, search=search, exportJob=exportJob, clusters=clusters))
        raise cherrypy.HTTPRedirect(self.make_url(['custom', app, 'exportjobs', 'success']), 303)


    @expose_page(must_login=True, methods=['POST'])
    @route('/:action=submitREDList', methods=['POST'])
    def submitREDList(self, action, **kwargs):
        '''accept a post of the information needed to create a HDFS Export Job'''
        user = cherrypy.session['user']['name']
        app = cherrypy.request.path_info.split('/')[3]

        successfullSave, exportJob = self.saveRED(user, app, **kwargs)
        if not successfullSave:
            logger.error("Could not save export job: %s" % exportJob.errors)
            return self.renderList(exportJob)
        raise cherrypy.HTTPRedirect(self.make_url(['custom', app, 'exportjobs', 'list']), 303)

    def saveRED(self, user, app, **kwargs):
        '''Save the scheduled HDFS export, return a tuple of the success and the modal'''

        keys = kwargs.keys()
        partitions = []
        for k in keys:
            if k.startswith('partition_'):# and splunk.util.normalizeBoolean(kwargs.get(k, 'f')):
               partitions.append(k[len('partition_'):])
               del kwargs[k]

        if len(partitions) > 0:
           kwargs['partition_fields'] = ','.join(partitions)

        exportJob = HDFSExport(app, user, **kwargs)
        exportJob.metadata.sharing = 'app'
        exportJob.metadata.owner = user
        exportJob.metadata.app = app
        logger.info("ExportJob errors: %s" % exportJob.errors)
        return (exportJob.passive_save(), exportJob)


    @expose_page(must_login=True, methods=['POST'])
    @route('/:action=delete', methods=['POST'])
    def delete(self, action, id=None, **kwargs):
        '''Delete a export job'''
        return self.custom_action(action, id)


    @expose_page(must_login=True, methods=['POST'])
    @route('/:action=force', methods=['POST'])
    def force(self, action, id=None, **kwargs):
        '''force the export job's execution to be now'''
        return self.custom_action(action, id)

    @expose_page(must_login=True, methods=['POST'])
    @route('/:action=pause', methods=['POST'])
    def pause(self, action, id=None, **kwargs):
        '''pause the export job's execution '''
        return self.custom_action(action, id)

    @expose_page(must_login=True, methods=['POST'])
    @route('/:action=resume', methods=['POST'])
    def resume(self, action, id=None, **kwargs):
        '''resume the export job's execution '''
        return self.custom_action(action, id)

    def custom_action(self, action, id):
        app = cherrypy.request.path_info.split('/')[3]
        done = False
        try:
            exportJob = HDFSExport.get(id)
            done = getattr(exportJob, action)()
        #do we need generic exception here?
        except Exception, e:
            logger.warn('Could not %s export job: %s, %s' % (action, id, str(e)))
        if done:
            raise cherrypy.HTTPRedirect(self.make_url(['custom', app, 'exportjobs', 'list']), 303)
        return self.renderList(listErrors = ['Could not %s export job: %s' % (action, id)])

    @expose_page(must_login=True, methods=['GET'])
    @route('/:action=details', methods=['GET'])
    def details(self, action, id=None, **kwargs):
        '''show the details of the export job'''
        app = cherrypy.request.path_info.split('/')[3]
        try:
            exportJob = HDFSExport.get(id)
        except:
            logger.warn('Could not find export job: %s' % id)
            #TODO: return something meaningful here
        return self.render_template('/%s:/templates/details.html' % app,
                                    dict(app=app, id=id, exportJob=exportJob))


    @expose_page(must_login=True, trim_spaces=True, methods='GET')
    @route('/:action=success', methods=['GET'])
    def success(self, action, **params):
        '''Display successful completion of modal'''
        app = cherrypy.request.path_info.split('/')[3]
        return self.render_template('/%s:/templates/success.html' % app, dict(form_content='fomasdafe', app=app))
